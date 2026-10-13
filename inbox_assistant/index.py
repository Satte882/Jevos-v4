"""Lesende Bestandsaufnahme und deterministische Vorauswahl für Obsidian."""
from __future__ import annotations

import hashlib
import re
import math
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

MAX_NOTE = 64 * 1024
MAX_ANALYSIS_TEXT = 12_000
MAX_REF_TEXT = 700
MAX_CANDIDATES = 8
IGNORED = {".obsidian", ".git", ".trash", ".local", "node_modules", "__pycache__"}
STOP = set("und oder aber doch den dem der die das ein eine einer einem einen auf mit ohne von für zum zur im in am an zu aus bei über unter ist sind als noch ich du wir ihr sie er es was wie wenn dann auch nicht mehr mein meine this that with from have them about when where your into notes note file".split())
STOP.update("the and for are you our their can will has its not all also how why welche dieser diese dieses durch wird werden einer eines sich auch sowie dazu damit hier dort dabei sein sehr beispielsweise beispiel können kann soll sollte müssen neue neuen erste ersten http https www com source title created description png jpg pasted image".split())
STOP.update("bedeutet bedeutung wichtig wichtigsten schlüsselkomponenten herausforderungen jahr organisation organisationen unternehmen unternehmensorganisationen wahrscheinlich vorbereitet lösen löst erklärt schließen sicherstellung unverzichtbar".split())
GENERIC_TOPICS = {"ai", "data", "model", "models", "business"}


def content_text(text: str) -> str:
    """Lesbarer Inhalt ohne Metadaten, URL-Tokens oder Bildreferenzen."""
    text = re.sub(r"\A---\s*\n.*?\n---\s*\n", "", text, count=1, flags=re.S)
    text = re.sub(r"!\[\[.*?\]\]|!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"^\s*\|?[ :|\-]{4,}\s*$", "", text, flags=re.M)
    return text.strip()


def relevant_excerpt(text: str, query: str, budget: int = 1400) -> str:
    """Auszüge über den gesamten Text; keine generierte Zusammenfassung."""
    clean = content_text(text)
    if len(clean) <= budget:
        return clean
    chunks = [s.strip() for s in re.split(r"\n\s*\n", clean) if s.strip()]
    q = tokens(query)
    if budget <= 400:
        passages = [s for s in chunks if len(s) >= 60 and not s.startswith("#")] or chunks
        best = max(passages, key=lambda s: (len((q - GENERIC_TOPICS) & tokens(s)),
                                            len(q & tokens(s)), -chunks.index(s)))
        return best[:budget]
    ranked = sorted(range(len(chunks)), key=lambda i: (-len(q & tokens(chunks[i])), i))
    selected = {0}
    remaining = budget - min(len(chunks[0]), 250) - 10
    for i in ranked:
        if i == 0 or remaining < 80:
            continue
        selected.add(i)
        remaining -= min(len(chunks[i]), 450) + 10
    excerpts = [chunks[i][:250 if i == 0 else 450] for i in sorted(selected)]
    return "\n[…]\n".join(excerpts)[:budget]


def archived(folder: str) -> bool:
    return bool(re.search(r"archiv|backlog|trash|papierkorb", folder, re.I))


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
    s = re.sub(r"daten[ -]?mesh", "data mesh", s, flags=re.I)
    s = re.sub(r"datenverwaltung|datenmanagement", "data governance management", s, flags=re.I)
    s = re.sub(r"datenqualität", "data quality", s, flags=re.I)
    s = re.sub(r"f[öe]deriert\w*", "federated", s, flags=re.I)
    s = re.sub(r"\bki\b", "ai", s, flags=re.I)
    s = re.sub(r"\b(?:risik\w*|risk\w*)", "risk", s, flags=re.I)
    s = re.sub(r"\b(?:skalier\w*|scaling|scalability)", "scaling", s, flags=re.I)
    s = re.sub(r"\bnativ\w*", "native", s, flags=re.I)
    return {w for w in re.findall(r"[^\W\d_]{2,}", s.lower(), flags=re.UNICODE)
            if w not in STOP and (len(w) >= 3 or w in {"ai", "ml"})}


@dataclass
class Note:
    source: str
    sha256: str
    text: str

    @property
    def title(self) -> str:
        return Path(self.source).stem


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
        self._cache = {}
        self.idf = {}
        self.reload()

    def _note(self, file: Path) -> Note | None:
        if file.is_symlink() or file.suffix.lower() != ".md":
            return None
        try:
            if file.stat().st_size > MAX_NOTE:
                return None
            stat = file.stat()
            key = (stat.st_mtime_ns, stat.st_size)
            cached = self._cache.get(file)
            if cached and cached[0] == key:
                return cached[1]
            note = Note(normalized(self.root, file), file_sha(file),
                        file.read_text(encoding="utf-8-sig"))
            self._cache[file] = (key, note)
            return note
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
        docs = [tokens(n.title + " " + content_text(n.text)[:MAX_ANALYSIS_TEXT])
                for refs in self.references.values() for n in refs]
        counts = Counter(word for doc in docs for word in doc)
        self.idf = {word: math.log(1 + (len(docs) + 1) / (count + 1))
                    for word, count in counts.items()}

    def relevance(self, query: Note, reference: Note) -> float:
        title = tokens(query.title)
        q = tokens(content_text(query.text)[:MAX_ANALYSIS_TEXT]) | title
        rt = tokens(reference.title)
        body = tokens(content_text(reference.text)[:MAX_ANALYSIS_TEXT])
        score = sum(self.idf.get(w, 1) * (0.3 if w in GENERIC_TOPICS else 1) *
                    (6 if w in title else 1) * (4 if w in rt else 1)
                    for w in q & (rt | body))
        # Topic words in a note title must outweigh broad vocabulary overlap.
        subject = title - GENERIC_TOPICS
        subject_score = sum(self.idf.get(w, 1) * (10 if w in rt else 4)
                            for w in subject & (rt | body))
        return subject_score + score / math.sqrt(max(1, len(body)))

    def pick_references(self, folder: str, note: Note, state: dict, limit: int = 3) -> list[Note]:
        options = self.references.get(folder, [])
        excluded = set(state.get("excluded_references", []))
        pins = state.get("pinned_references", {}).get(folder, [])
        relevant = [n for n in options if n.source not in excluded]
        pinned = [n for source in pins for n in relevant if n.source == source]
        remaining = [n for n in relevant if n not in pinned]
        remaining.sort(key=lambda n: (-self.relevance(note, n), n.source))
        return (pinned + remaining)[:limit]

    def candidates(self, note: Note, state: dict, limit: int = MAX_CANDIDATES) -> list[dict]:
        words = tokens(note.title + " " + content_text(note.text)[:MAX_ANALYSIS_TEXT])
        title_words = tokens(note.title)
        folders = []
        for folder in self.folders:
            if archived(folder) and not state.get("include_archives", False):
                continue
            refs = self.pick_references(folder, note, state)
            folder_score = sum((14 if w in title_words else 2) * self.idf.get(w, 1) * (0.3 if w in GENERIC_TOPICS else 1)
                                   for w in words & tokens(folder.replace("/", " ")))
            ref_score = max((self.relevance(note, n) for n in refs), default=0)
            folders.append((folder_score + ref_score, folder, refs))
        folders.sort(key=lambda t: (-t[0], t[1]))
        return [{"folder": folder, "match": round(score, 3),
                 "references": [{"source": ref.source, "title": ref.title,
                                 "model_snippet": relevant_excerpt(ref.text, note.title, 180),
                                 "snippet": relevant_excerpt(ref.text, note.title, MAX_REF_TEXT)}
                                for ref in refs]}
                for score, folder, refs in folders[:limit]]

    def references_for_ui(self, folder: str, state: dict) -> list[dict]:
        if folder not in self.folders:
            raise ValueError("Unbekannter Zielordner.")
        excluded = set(state.get("excluded_references", []))
        pinned = set(state.get("pinned_references", {}).get(folder, []))
        return [{"source": n.source, "excluded": n.source in excluded, "pinned": n.source in pinned}
                for n in self.references.get(folder, [])]
