"""Deterministische lokale PII-Bereinigung mit spaCy-NER und transparenten Grenzen."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

MAX_TEXT_CHARS = 100_000

# Explizit priorisierte Treffer. Spätere Regeln dürfen frühere nicht überschreiben.
REGEX = [
    ("SECRET", re.compile(r"(?i)\b(?:sk-[a-z0-9_-]{12,}|gh[pousr]_[a-z0-9]{18,}|xox[baprs]-[a-z0-9-]{12,})\b")),
    ("SECRET", re.compile(r"(?i)\b(?:api[_ -]?key|password|passwort|access[_ -]?token|client[_ -]?secret)\s*[:=]\s*[\"']?[^\s\"']{6,}")),
    ("EMAIL", re.compile(r"(?i)(?<![\w.+-])[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}(?!\w)")),
    ("URL", re.compile(r"(?i)(?:https?://|www\.)[^\s<>\"']+")),
    ("IBAN", re.compile(r"(?i)\bDE(?:[ \t]?[0-9]){20}\b")),
    ("PHONE", re.compile(r"(?<!\w)(?:\+49|0049|0)[ \t()/-]*(?:[0-9][ \t()/-]*){7,13}(?!\w)")),
    ("IP", re.compile(r"(?<![\w.])(?:[0-9]{1,3}\.){3}[0-9]{1,3}(?![\w.])")),
]
ENTITY_LABELS = {
    "PER": "PERSON", "PERSON": "PERSON",
    "ORG": "UNTERNEHMEN",
    "LOC": "ORT", "GPE": "ORT", "FAC": "ORT",
}


@dataclass(frozen=True)
class Finding:
    start: int
    end: int
    label: str
    original: str
    priority: int


@lru_cache(maxsize=1)
def _load_model():
    """Ohne deutsches lokales NER-Modell keine vermeintlich vollständige Bereinigung."""
    try:
        import spacy
    except ImportError as exc:
        raise RuntimeError(
            "Die lokale Erkennung fehlt: zuerst scripts/setup-redaction.ps1 ausführen."
        ) from exc
    model = None
    for name in ("de_core_news_md", "de_core_news_sm"):
        try:
            model = spacy.load(name, disable=["parser", "tagger", "lemmatizer"])
            break
        except OSError:
            continue
    if model is None or "ner" not in model.pipe_names:
        raise RuntimeError(
            "Kein lokales deutsches spaCy-NER-Modell installiert. "
            "Bitte scripts/setup-redaction.ps1 ausführen."
        )
    return model


def _ner(text: str) -> list[Finding]:
    # Nur lokale Pipeline; in jedem Prozess einmal geladen.
    doc = _load_model()(text)
    return [
        Finding(ent.start_char, ent.end_char, ENTITY_LABELS[ent.label_], ent.text, 10)
        for ent in doc.ents
        if ent.label_ in ENTITY_LABELS and ent.text.strip()
    ]


def _regex_findings(text: str) -> list[Finding]:
    result = []
    for priority, (label, pattern) in enumerate(REGEX):
        for match in pattern.finditer(text):
            start, end = match.span()
            # URLs mit üblicher Satzzeichen-Interpunktion abschneiden.
            if label == "URL":
                while end > start and text[end - 1] in ".,;:!?)]":
                    end -= 1
            if label == "IP":
                from ipaddress import ip_address
                try:
                    ip_address(text[start:end])
                except ValueError:
                    continue
            if end > start:
                result.append(Finding(start, end, label, text[start:end], priority))
    return result


def redact(text: str, *, entities: list[Finding] | None = None) -> dict:
    """Text bereinigen; Metadaten enthalten keine Originaltreffer.

    entities ist nur für isolierte Tests; im Normalbetrieb zwingend lokales spaCy.
    """
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Bitte einen Text eingeben.")
    if len(text) > MAX_TEXT_CHARS:
        raise ValueError(f"Maximal {MAX_TEXT_CHARS:,} Zeichen sind erlaubt.")

    detected = _regex_findings(text) + (_ner(text) if entities is None else entities)
    # Überlappungen: möglichst großer Treffer mit höher priorisierter Kategorie.
    detected.sort(key=lambda item: (item.start, item.priority, -(item.end-item.start)))
    accepted: list[Finding] = []
    occupied_until = -1
    for item in detected:
        if item.start < 0 or item.end > len(text) or item.start >= item.end:
            continue
        if item.start < occupied_until:
            continue
        accepted.append(item)
        occupied_until = item.end

    mapping: dict[tuple[str, str], str] = {}
    counts: Counter[str] = Counter()
    parts: list[str] = []
    pos = 0
    for item in accepted:
        parts.append(text[pos:item.start])
        # identische Namen werden pro Anfrage konsistent durch denselben Platzhalter ersetzt
        key = (item.label, " ".join(item.original.casefold().split()))
        if key not in mapping:
            counts[item.label] += 1
            mapping[key] = f"[{item.label}_{counts[item.label]}]"
        parts.append(mapping[key])
        pos = item.end
    parts.append(text[pos:])
    sanitized = "".join(parts)

    return {
        "text": sanitized,
        "categories": dict(counts),
        "replacements": len(accepted),
        "warnings": [
            "Automatische Erkennung kann Namen, Geschäftsgeheimnisse oder indirekte Identifikatoren übersehen.",
            "Bitte auch Rollen, seltene Ereignisse, Datumsangaben, Beträge und Kombinationen von Details manuell prüfen.",
            "Das Ergebnis ist zunächst bereinigter bzw. pseudonymisierter Text, keine garantierte Anonymisierung.",
        ],
    }
