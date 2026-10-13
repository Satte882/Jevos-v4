"""Domänenservice – prüfbare Inbox-Vorschläge und menschliche Freigabe."""
from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path

from jevos_local.client import JevosClient, TypeSafeClient, JevosError
from .bridge import bridge_status, stage_moves
from .index import VaultIndex, file_sha, safe_path
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
        self.state_path = self.workdir / "assistant-state.json"
        self.bridge_dir = self.workdir / "bridge"
        self.backup_dir = self.workdir / "backups"
        self.state = load(self.state_path)
        self.lock = threading.RLock()

    def save(self):
        atomic_json(self.state_path, self.state)

    def overview(self) -> dict:
        with self.lock:
            self.index.reload()
            current = {n.source: n for n in self.index.inbox_notes}
            rows = []
            for note in self.index.inbox_notes:
                analysis = self.state["analyses"].get(note.source)
                if analysis and analysis.get("sha256") != note.sha256:
                    analysis = None
                decision = self.state["decisions"].get(note.source)
                if decision and decision.get("sha256") != note.sha256:
                    decision = None
                rows.append({"source": note.source, "sha256": note.sha256,
                             "analysis": analysis, "decision": decision})
            return {"rows": rows, "folders": self.index.folders,
                    "inbox": self.index.inbox_rel, "vault": str(self.index.root),
                    "bridge": bridge_status(self.bridge_dir),
                    "provider": ["local", "jev"]}

    def note(self, source: str) -> str:
        with self.lock:
            return self._get_note(source).text

    def _get_note(self, source: str):
        self.index.reload()
        note = next((n for n in self.index.inbox_notes if n.source == source), None)
        if note is None:
            raise ValueError("Notiz nicht mehr in der Inbox.")
        safe_path(self.index.root, note.source)
        return note

    def references(self, folder: str) -> list[dict]:
        with self.lock:
            self.index.reload()
            return self.index.references_for_ui(folder, self.state)

    def reference_action(self, folder: str, source: str, action: str) -> dict:
        with self.lock:
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
            self.save()
            return {"ok": True, "references": self.index.references_for_ui(folder, self.state)}

    def analyze(self, provider: str, *, cloud_consent: bool = False, limit: int = 20) -> dict:
        with self.lock:
            if provider not in ("local", "jev"):
                raise ValueError("Provider muss explizit local oder jev sein.")
            if provider == "jev" and not cloud_consent:
                raise ValueError("Cloud-Übertragung muss ausdrücklich freigegeben werden.")
            if not 1 <= limit <= 50:
                raise ValueError("Bitte 1–50 Notizen auswählen.")
            client = JevosClient() if provider == "local" else TypeSafeClient()
            self.index.reload()
            results = []
            errors = []
            for note in self.index.inbox_notes[:limit]:
                candidates = self.index.candidates(note, self.state)
                if not candidates:
                    errors.append({"source": note.source, "error": "Keine Zielordner vorhanden."})
                    continue
                criteria = {}
                for i, candidate in enumerate(candidates, 1):
                    examples = "; ".join(
                        f"{r['source']}: {r['snippet'][:240]}"
                        for r in candidate["references"][:2]
                    )
                    criteria[f"f{i}"] = f"Existing folder: {candidate['folder']}. Example notes: {examples}"
                criteria["none"] = "None of the available folders fits the note reasonably well."
                prompt = ("Choose the BEST existing destination folder for this Obsidian note. "
                          "Consider the topic and the examples; choose none if no good fit.")
                context = f"Filename: {note.source}\nNote content:\n{note.text}"
                try:
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
                            r["source"] for c in candidates for r in c["references"]}),
                        "candidate_folders": [c["folder"] for c in candidates],
                    }
                    self.state["analyses"][note.source] = result
                    # Bei erneuter Analyse keine alte Freigabe übernehmen.
                    self.state["decisions"].pop(note.source, None)
                    self.save()
                    results.append({"source": note.source, "analysis": result})
                except (JevosError, KeyError, ValueError) as exc:
                    errors.append({"source": note.source, "error": str(exc)})
            return {"provider": provider, "results": results, "errors": errors,
                    "total": len(results), "review_needed": sum(
                        r["analysis"]["manual_review"] for r in results)}

    def decide(self, source: str, status: str, destination: str | None = None) -> dict:
        with self.lock:
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
            # Der Browser fordert eine separate Aktion ausdrücklich an.
            return stage_moves(self.index, self.state, self.bridge_dir, self.backup_dir,
                               self.state["decisions"])
