"""Lesende Bestandsaufnahme und deterministische Vorauswahl für Obsidian."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

MAX_NOTE = 64 * 1024
MAX_ANALYSIS_TEXT = 9000
MAX_REF_TEXT = 700
MAX_CANDIDATES = 8
IGNORED = {".obsidian", ".git", ".trash", ".local", "node_modules", "__pycache__"}
STOP = set("und oder aber doch den dem der die das ein eine einer einem einen auf mit ohne von für zum zur im in am an zu aus bei über unter ist sind als noch ich du wir ihr sie er es was wie wenn dann auch nicht mehr mein meine this that with from have them about when where your into notes note file".split())


def rooted(root: str | Path, path: str | Path) -> Path:
    base = Path(root).expanduser().resolve(strict=True)
    result = Path(path).expanduser().resolve(strict=True)
    if not result.is_relative_to(base):
        raise ValueError("Pfad außerhalb des Obsidian-Vaults.")
    return result


def normalized(root: Path, file: Path) -> str:
    return file.relative_to(root).as_posix()


def safe_path(root: Path, relative: str, *, exists: bool = True) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative or relative.startswith("/"):
        raise ValueError("Ungültiger relativer Vault-Pfad.")
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Ungültiger relativer Vault-Pfad.")
    candidate = root.joinpath(*parts)
    if candidate.is_symlink():
        raise ValueError("Symbolische Links sind nicht erlaubt.")
    real = candidate.resolve(strict=exists)
    if not real.is_relative_to(root):
        raise ValueError("Pfad verlässt den Vault.")
    return real


def file_sha(file: Path) -> str:
    return hashlib.sha256(file.read_bytes()).hexdigest()


def tokens(s: str) -> set[str]:
    return {w for w in re.findall(r"[^\W\d_]{3,}", s.lower(), flags=re.UNICODE)
            if w not in STOP}


@dataclass
class Note:
    source: str
    sha256: str
    text: str


class VaultIndex:
    def __init__(self, vault: str | Path, inbox: str | Path):
        self.root = Path(vault).expanduser().resolve(strict=True)
        self.inbox = rooted(self.root, inbox)
        if not self.inbox.is_dir() or self.inbox == self.root:
            raise ValueError("Der Inbox-Pfad muss ein Unterordner des Vaults sein.")
        self.inbox_rel = normalized(self.root, self.inbox)
        self.inbox_notes: list[Note] = []
        self.folders: list[str] = []
        self.references: dict[str, list[Note]] = {}
        self.reload()

    def _note(self, file: Path) -> Note | None:
        if file.is_symlink() or file.suffix.lower() != ".md":
            return None
        try:
            if file.stat().st_size > MAX_NOTE:
                return None
            return Note(normalized(self.root, file), file_sha(file),
                        file.read_text(encoding="utf-8-sig")[:MAX_ANALYSIS_TEXT])
        except (UnicodeError, OSError):
            return None

    def reload(self):
        self.inbox_notes = []
        self.folders = []
        self.references = {}
        # MVP: nur Markdown-Dateien direkt in der Inbox.
        for file in sorted(self.inbox.iterdir()):
            if file.is_file() and not file.name.startswith("."):
                note = self._note(file)
                if note and note.text.strip():
                    self.inbox_notes.append(note)
        # Keine Symlinks, keine versteckten Systemordner und keine Inbox-Ziele.
        import os
        for base, dirs, files in os.walk(self.root, followlinks=False):
            current = Path(base)
            dirs[:] = sorted(d for d in dirs if d not in IGNORED and
                             not d.startswith(".") and not (current / d).is_symlink()
                             and (current / d).resolve() != self.inbox)
            if current == self.root:
                continue
            folder = normalized(self.root, current)
            if folder == self.inbox_rel or folder.startswith(self.inbox_rel + "/"):
                dirs.clear()
                continue
            self.folders.append(folder)
            selected = []
            for name in sorted(files):
                file = current / name
                if name.startswith(".") or file.is_symlink():
                    continue
                note = self._note(file)
                if note and note.text.strip():
                    selected.append(note)
                if len(selected) >= 50:  # Begrenzter lesender Index pro Ordner
                    break
            self.references[folder] = selected

    def pick_references(self, folder: str, note: Note, state: dict, limit: int = 3) -> list[Note]:
        options = self.references.get(folder, [])
        excluded = set(state.get("excluded_references", []))
        pins = state.get("pinned_references", {}).get(folder, [])
        relevant = [n for n in options if n.source not in excluded]
        pinned = [n for source in pins for n in relevant if n.source == source]
        remaining = [n for n in relevant if n not in pinned]
        q = tokens(note.source + " " + note.text[:1200])
        remaining.sort(key=lambda n: (len(q & tokens(n.source + " " + n.text[:1200])),
                                      n.source), reverse=True)
        return (pinned + remaining)[:limit]

    def candidates(self, note: Note, state: dict, limit: int = MAX_CANDIDATES) -> list[dict]:
        words = tokens(note.source + " " + note.text[:2500])
        folders = []
        for folder in self.folders:
            refs = self.pick_references(folder, note, state)
            folder_score = 3 * len(words & tokens(folder.replace("/", " ")))
            ref_score = max((len(words & tokens(n.source + " " + n.text[:1200])) for n in refs), default=0)
            folders.append((folder_score + ref_score, folder, refs))
        folders.sort(key=lambda t: (-t[0], t[1]))
        return [{"folder": folder, "match": score,
                 "references": [{"source": ref.source, "snippet": ref.text[:MAX_REF_TEXT]}
                                for ref in refs]}
                for score, folder, refs in folders[:limit]]

    def references_for_ui(self, folder: str, state: dict) -> list[dict]:
        if folder not in self.folders:
            raise ValueError("Unbekannter Zielordner.")
        excluded = set(state.get("excluded_references", []))
        pinned = set(state.get("pinned_references", {}).get(folder, []))
        return [{"source": n.source, "excluded": n.source in excluded, "pinned": n.source in pinned}
                for n in self.references.get(folder, [])]
