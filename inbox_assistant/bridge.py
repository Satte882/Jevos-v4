"""Sicherungs-ZIP und expliziter Übergabeplan für das Obsidian-Plugin."""
from __future__ import annotations

import hashlib
import json
import os
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from .index import safe_path, file_sha
from .store import atomic_json, load


def stage_moves(index, state: dict, bridge_dir: Path, backup_dir: Path, decisions: dict) -> dict:
    """Erst nach expliziter Web-Freigabe; es werden keine Notizen verschoben."""
    pending_file = bridge_dir / "pending.json"
    result_file = bridge_dir / "result.json"
    if pending_file.exists():
        previous = load(pending_file)
        result = load(result_file) if result_file.exists() else {}
        if previous.get("batch_id") != result.get("batch_id"):
            raise ValueError("Ein vorheriger Stapel wartet noch auf die Ausführung in Obsidian.")
    index.reload()
    available = {note.source: note for note in index.inbox_notes}
    destinations = set(index.folders)
    moves = []
    for source, decision in sorted(decisions.items()):
        if decision.get("status") != "approved":
            continue
        note = available.get(source)
        if note is None or note.sha256 != decision.get("sha256"):
            raise ValueError(f"Notiz geändert/verschwunden, bitte erneut prüfen: {source}")
        dest_folder = decision.get("destination")
        if dest_folder not in destinations:
            raise ValueError(f"Ungültiger Zielordner für {source}")
        from_path = safe_path(index.root, source)
        to_rel = dest_folder + "/" + from_path.name
        target = safe_path(index.root, to_rel, exists=False)
        if target.exists():
            raise ValueError(f"Zieldatei existiert bereits: {to_rel}")
        moves.append({"source": source, "target": to_rel, "sha256": note.sha256})
    if not moves:
        raise ValueError("Keine bestätigten Notizen zum Verschieben vorhanden.")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = backup_dir / f"obsidian-{stamp}-{uuid.uuid4().hex[:8]}.zip"
    backup = backup_notes(index.root, backup_path, moves)
    plan = {
        "version": 1,
        "batch_id": uuid.uuid4().hex,
        "vault": str(index.root),
        "inbox": index.inbox_rel,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "backup": backup,
        "moves": moves,
        "status": "awaiting-obsidian",
    }
    bridge_dir.mkdir(parents=True, exist_ok=True)
    # Altes Resultat nur nach erfolgreichem Backup/Plan-Versand zurücksetzen.
    atomic_json(pending_file, plan)
    result_file.unlink(missing_ok=True)
    return plan


def backup_notes(vault: Path, destination: Path, moves: list) -> dict:
    """Save editable link-bearing documents, never large media attachments.

    Conservatively include every Markdown/Canvas document: Obsidian resolves
    links and may rewrite documents beyond the backend's reference index.
    The manifest records exact originals and both paths for manual recovery.
    """
    if destination.resolve().is_relative_to(vault):
        raise ValueError("Backups dürfen nicht im Vault liegen.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".partial")
    entries = []
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED,
                             compresslevel=1, allowZip64=True) as archive:
            for directory, dirs, files in os.walk(vault, followlinks=False):
                root = Path(directory)
                dirs[:] = sorted(d for d in dirs if d not in {".obsidian", ".git", ".trash", ".local"})
                if any((root / d).is_symlink() for d in dirs):
                    raise ValueError("Symlink im Vault; Notizsicherung nicht verifizierbar.")
                for name in sorted(files):
                    file = root / name
                    if file.suffix.lower() not in {".md", ".canvas"}:
                        continue
                    if file.is_symlink():
                        raise ValueError("Symlink in Notizen; Sicherung wird abgebrochen.")
                    data = file.read_bytes()
                    source = file.relative_to(vault).as_posix()
                    archive.writestr(source, data)
                    entries.append({"source": source, "sha256": hashlib.sha256(data).hexdigest()})
            original_hashes = {e["source"]: e["sha256"] for e in entries}
            if any(original_hashes.get(m["source"]) != m["sha256"] for m in moves):
                raise ValueError("Notiz während der Sicherung geändert; erneut prüfen.")
            archive.writestr("_jev_recovery.json", json.dumps({"vault": str(vault), "moves": moves,
                              "entries": entries}, ensure_ascii=False, indent=2))
        with zipfile.ZipFile(temporary) as archive:
            if archive.testzip() is not None:
                raise ValueError("Notizsicherung beschädigt.")
        os.replace(temporary, destination)
        with destination.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        return {"path": str(destination), "sha256": digest, "files": len(entries),
                "scope": "link-documents", "entries": entries}
    finally:
        temporary.unlink(missing_ok=True)


def bridge_status(bridge_dir: Path) -> dict:
    pending = bridge_dir / "pending.json"
    if not pending.exists():
        return {"status": "none"}
    plan = load(pending)
    result_file = bridge_dir / "result.json"
    result = load(result_file) if result_file.exists() else {}
    if result.get("batch_id") == plan.get("batch_id"):
        return {"status": "finished", "batch_id": plan.get("batch_id"),
                "results": result.get("results", []), "backup": plan.get("backup", {})}
    return {"status": "awaiting-obsidian", "batch_id": plan.get("batch_id"),
            "moves": [{"source": m["source"], "target": m["target"]} for m in plan.get("moves", [])],
            "backup": plan.get("backup", {})}
