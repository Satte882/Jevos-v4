"""Domänenservice – prüfbare Inbox-Vorschläge und menschliche Freigabe."""
from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

from jevos_local.client import JevosClient, TypeSafeClient, JevosError
from .bridge import bridge_status, stage_moves
from .index import VaultIndex, file_sha, safe_path, relevant_excerpt, content_text
from .store import load, atomic_json

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config.example.json"


class InboxService:
    def __init__(self, config: str | Path | None = None):
        config_path = Path(config) if config else DEFAULT_CONFIG
        values = json.loads(config_path.read_text(encoding="utf-8"))
        self.repo = Path(__file__).resolve().parent.parent
        self.index = VaultIndex(values["vault"], values["inbox"])
        if self.repo.resolve().is_relative_to(self.index.root):
            raise ValueError("Das Entwicklungsrepo muss außerhalb des Obsidian-Vaults liegen.")
        self.workdir = self.repo / ".local"
        vault_id = hashlib.sha256(str(self.index.root).casefold().encode()).hexdigest()[:16]
        self.state_path = self.workdir / "vault-state" / (vault_id + ".json")
        self.bridge_dir = self.workdir / "bridge"
        self.backup_dir = self.workdir / "backups"
        self.state = load(self.state_path)
        self.lock = threading.RLock()
        self.busy = False
        self.job = {"status": "idle"}
        self.last_scan = 0

    def _bridge_status(self):
        pending = self.bridge_dir / "pending.json"
        if pending.exists() and load(pending).get("vault") != str(self.index.root):
            return {"status": "none"}
        return bridge_status(self.bridge_dir)

    def save(self):
        atomic_json(self.state_path, self.state)

    def _reconcile(self):
        """Abgeschlossene Obsidian-Ergebnisse nur einmal übernehmen."""
        bridge = self._bridge_status()
        if bridge["status"] == "finished" and self.state.get("last_reconciled") != bridge["batch_id"]:
            for row in bridge["results"]:
                source = row.get("source")
                decision = self.state["decisions"].get(source)
                if decision and row.get("status") == "moved":
                    decision["status"] = "moved"
            self.state["last_reconciled"] = bridge["batch_id"]
            self.save()

    def _require_idle(self):
        self._reconcile()
        if self.busy:
            raise ValueError("Die Analyse läuft noch; bitte zuerst abschließen lassen.")
        if bridge_status(self.bridge_dir)["status"] == "awaiting-obsidian":
            raise ValueError("Ein Verschiebungsstapel wartet auf Obsidian; zuerst abschließen.")

    def overview(self) -> dict:
        with self.lock:
            self._reconcile()
            if not self.busy and time.monotonic() - self.last_scan > 5:
                self.index.reload()
                self.last_scan = time.monotonic()
            rows = []
            for note in self.index.inbox_notes:
                analysis = self.state["analyses"].get(note.source)
                if analysis and analysis.get("sha256") != note.sha256:
                    analysis = None
                decision = self.state["decisions"].get(note.source)
                if decision and decision.get("sha256") != note.sha256:
                    decision = None
                error = self.state.get("errors", {}).get(note.source)
                if error and error.get("sha256") != note.sha256:
                    error = None
                rows.append({"source": note.source, "sha256": note.sha256,
                             "title": note.title,
                             "preview": relevant_excerpt(note.text, note.title, 1800),
                             "characters": len(note.text),
                             "error": error,
                             "analysis": analysis, "decision": decision})
            return {"rows": rows, "folders": self.index.folders,
                    "inbox": self.index.inbox_rel, "vault": str(self.index.root),
                    "bridge": self._bridge_status(), "job": dict(self.job),
                    "include_archives": self.state.get("include_archives", False),
                    "provider": ["local", "jev"]}

    def note(self, source: str) -> str:
        with self.lock:
            return self._get_note(source).text

    def _get_note(self, source: str):
        file = safe_path(self.index.root, source)
        if file.parent != self.index.inbox or file.name.startswith(".") or not file.is_file():
            raise ValueError("Notiz nicht mehr in der Inbox.")
        note = self.index._note(file)
        if note is None:
            raise ValueError("Notiz nicht mehr in der Inbox.")
        return note

    def references(self, folder: str) -> list[dict]:
        with self.lock:
            if not self.busy:
                self.index.reload()
            return self.index.references_for_ui(folder, self.state)

    def reference_action(self, folder: str, source: str, action: str) -> dict:
        with self.lock:
            self._require_idle()
            self.index.reload()
            items = self.index.references_for_ui(folder, self.state)
            if source not in {item["source"] for item in items}:
                raise ValueError("Referenz gehört nicht zum ausgewählten Zielordner.")
            excluded = set(self.state["excluded_references"])
            pinned = self.state["pinned_references"].setdefault(folder, [])
            if action == "exclude":
                excluded.add(source)
                if source in pinned:
                    pinned.remove(source)
            elif action == "include":
                excluded.discard(source)
            elif action == "pin":
                excluded.discard(source)
                if source not in pinned:
                    pinned.insert(0, source)
            elif action == "unpin":
                if source in pinned:
                    pinned.remove(source)
            else:
                raise ValueError("Ungültige Referenzaktion.")
            self.state["excluded_references"] = sorted(excluded)
            # Korrekturen sollen sichtbar neue Vorschläge erzeugen.
            self.state["analyses"] = {}
            self.state["decisions"] = {}
            self.state["errors"] = {}
            self.save()
            return {"ok": True, "references": self.index.references_for_ui(folder, self.state)}

    def _validate_analysis(self, provider, cloud_consent, limit):
        if provider not in ("local", "jev"):
            raise ValueError("Provider muss explizit local oder jev sein.")
        if provider == "jev" and not cloud_consent:
            raise ValueError("Cloud-Übertragung muss ausdrücklich freigegeben werden.")
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 50:
            raise ValueError("Bitte 1–50 Notizen auswählen.")

    def start_analysis(self, provider, *, cloud_consent=False, limit=20, include_archives=False):
        with self.lock:
            self._validate_analysis(provider, cloud_consent, limit)
            self._require_idle()
            self.busy = True
            self.job = {"status": "running", "completed": 0, "total": 0, "current": "Inbox wird gelesen"}
        def worker():
            try:
                self.analyze(provider, cloud_consent=cloud_consent, limit=limit,
                             include_archives=include_archives, _reserved=True)
            except Exception as exc:
                with self.lock:
                    self.job = {"status": "failed", "error": str(exc)}
                    self.busy = False
        self.analysis_thread = threading.Thread(target=worker, daemon=True)
        self.analysis_thread.start()
        return {"started": True}

    def analyze(self, provider: str, *, cloud_consent: bool = False, limit: int = 20,
                include_archives: bool = False, _reserved: bool = False) -> dict:
        with self.lock:
            self._validate_analysis(provider, cloud_consent, limit)
            if not _reserved:
                self._require_idle()
                self.busy = True
                self.job = {"status": "running", "completed": 0, "total": 0}
        results, errors = [], []
        try:
            with self.lock:
                self.index.reload()
                self.last_scan = time.monotonic()
                notes = list(self.index.inbox_notes[:limit])
                self.state["include_archives"] = include_archives
                self.state.setdefault("errors", {})
                for note in notes:
                    self.state["analyses"].pop(note.source, None)
                    self.state["decisions"].pop(note.source, None)
                    self.state["errors"].pop(note.source, None)
                self.save()
                self.job.update(total=len(notes))
            client = JevosClient(timeout=90) if provider == "local" else TypeSafeClient()
            unavailable = None
            for note in notes:
                started = time.monotonic()
                with self.lock:
                    self.job["current"] = note.title
                candidates = self.index.candidates(note, self.state)
                # Bounded request: five folders and two short, relevant passages each.
                candidates = candidates[:5]
                criteria = {}
                evidence = []
                for i, candidate in enumerate(candidates, 1):
                    sent_refs = [{"source": r["source"], "title": r["title"],
                                  "snippet": r["model_snippet"]}
                                 for r in candidate["references"][:2]]
                    evidence.append({"folder": candidate["folder"], "match": candidate["match"],
                                     "references": sent_refs})
                    examples = "; ".join(
                        f"{r['title'][:70]}: {r['snippet']}" for r in sent_refs
                    )
                    criteria[f"f{i}"] = f"Folder: {candidate['folder']}. Examples: {examples}"
                criteria["none"] = "None of the available folders fits the note reasonably well."
                prompt = ("Choose the BEST existing destination folder for this Obsidian note. "
                          "Consider the topic and the examples; choose none if no good fit.")
                excerpt = relevant_excerpt(note.text, note.title, 1400)
                context = f"Title: {note.title}\nSelected passages:\n{excerpt}"
                try:
                    if unavailable:
                        raise JevosError("Nicht abgefragt: " + unavailable)
                    if not candidates:
                        raise ValueError("Keine geeigneten Zielordner vorhanden. Archivziele bei Bedarf einbeziehen.")
                    answer = client.ask(
                        context, {"destination": {"type": "choice", "instructions": prompt,
                                                 "criteria": criteria}}
                    )["destination"]
                    dist = answer.get("probabilities", {})
                    if not isinstance(dist, dict) or set(dist) != set(criteria):
                        raise JevosError("Unvollständige Choice-Verteilung.")
                    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or
                           not 0 <= v <= 1 for v in dist.values()):
                        raise JevosError("Ungültige Wahrscheinlichkeiten.")
                    sorted_ids = sorted(
                        (i for i in dist if i != "none"), key=lambda k: (-dist[k], k)
                    )
                    best = sorted_ids[0]
                    candidate_folders = {f"f{i}": c["folder"] for i, c in enumerate(candidates, 1)}
                    ranked = [{"folder": candidate_folders[key], "probability": round(dist[key], 4)}
                              for key in sorted_ids[:3]]
                    top = float(dist[best])
                    second = max((float(dist[k]) for k in dist if k != best), default=0)
                    uncertain = (answer.get("choice") == "none" or top < 0.45 or
                                 top - second < 0.07 or candidates[0]["match"] == 0)
                    result = {
                        "sha256": note.sha256, "provider": provider,
                        "primary": None if uncertain else ranked[0]["folder"],
                        "alternatives": ranked[:3], "manual_review": uncertain,
                        "model_confidence": answer.get("confidence"),
                        "reference_sources": sorted({
                            r["source"] for c in evidence for r in c["references"]}),
                        "evidence": evidence, "input_excerpt": excerpt,
                        "input_characters": len(excerpt), "note_characters": len(note.text),
                        "excerpted": len(content_text(note.text)) > len(excerpt),
                        "elapsed_seconds": round(time.monotonic() - started, 2),
                        "candidate_folders": [c["folder"] for c in candidates],
                    }
                    with self.lock:
                        self.state["analyses"][note.source] = result
                        self.save()
                    results.append({"source": note.source, "analysis": result})
                except (JevosError, KeyError, ValueError) as exc:
                    error = {"source": note.source, "error": str(exc), "sha256": note.sha256,
                             "elapsed_seconds": round(time.monotonic() - started, 2)}
                    errors.append(error)
                    with self.lock:
                        self.state["errors"][note.source] = error
                        self.save()
                    if isinstance(exc, JevosError) and isinstance(exc.__cause__, (TimeoutError, OSError)):
                        unavailable = str(exc)
                with self.lock:
                    self.job["completed"] += 1
            with self.lock:
                self.job.update(status="finished", successful=len(results), errors=len(errors), current=None)
            return {"provider": provider, "results": results, "errors": errors,
                    "total": len(results), "review_needed": sum(
                        r["analysis"]["manual_review"] for r in results)}
        except Exception as exc:
            with self.lock:
                self.job = {"status": "failed", "error": str(exc)}
            raise
        finally:
            with self.lock:
                self.busy = False

    def decide(self, source: str, status: str, destination: str | None = None) -> dict:
        with self.lock:
            self._require_idle()
            note = self._get_note(source)
            analysis = self.state["analyses"].get(note.source)
            if not analysis or analysis.get("sha256") != note.sha256:
                raise ValueError("Notiz muss mit aktuellem Stand analysiert werden.")
            if status not in ("approved", "deferred"):
                raise ValueError("Ungültiger Prüfstatus.")
            if status == "approved":
                if destination not in self.index.folders:
                    raise ValueError("Nur vorhandene Zielordner dürfen ausgewählt werden.")
            else:
                destination = None
            decision = {"sha256": note.sha256, "status": status, "destination": destination}
            self.state["decisions"][source] = decision
            self.save()
            return decision

    def prepare(self) -> dict:
        with self.lock:
            self._require_idle()
            # Der Browser fordert eine separate Aktion ausdrücklich an.
            return stage_moves(self.index, self.state, self.bridge_dir, self.backup_dir,
                               self.state["decisions"])

    def cancel_pending(self) -> dict:
        """Nicht ausgeführten Plan verwerfen; das Backup bleibt erhalten."""
        with self.lock:
            if bridge_status(self.bridge_dir)["status"] != "awaiting-obsidian":
                raise ValueError("Kein ausstehender Verschiebungsstapel.")
            (self.bridge_dir / "pending.json").unlink()
            return {"cancelled": True}
