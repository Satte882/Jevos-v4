"""Gemeinsame Entscheidungsfragen und Ausgabe für Jev und Jevos-v4."""
from __future__ import annotations

from .client import QUESTIONS, LABELS, JevosError

CHOICE = {
    "type": "choice",
    "instructions": "What is the main purpose of this note? Select the best category.",
    "criteria": {
        "task": "Concrete action to complete",
        "idea": "Suggestion for a future activity or project",
        "decision": "An unresolved choice",
        "information": "Reference material, facts, or background information",
    },
}
SCORE = {
    "type": "score",
    "instructions": "How urgently does this note require human action, based only on its text?",
    "criteria": ["No action needed", "Can wait", "Action needed soon", "Immediate action required"],
}
MODES = ("noul", "choice", "score", "all")
COLUMNS = {"source", "provider", "task_p", "idea_p", "decision_p",
           "task_yes", "idea_yes", "decision_yes", "category", "category_confidence",
           "urgency_score", "urgency_confidence"}


COLUMNS.update({"choice_" + key + "_p" for key in CHOICE["criteria"]})
COLUMNS.update({"urgency_" + str(i) + "_p" for i in range(4)})


def questions_for(mode: str) -> dict:
    if mode not in MODES:
        raise ValueError("Unbekannter Fragetyp.")
    questions = {}
    if mode in ("noul", "all"):
        questions.update(QUESTIONS)
    if mode in ("choice", "all"):
        questions["category"] = CHOICE
    if mode in ("score", "all"):
        questions["urgency"] = SCORE
    return questions


def _unit(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1:
        raise JevosError(f"Ungültige Wahrscheinlichkeit/Konfidenz: {label}")
    return float(value)


def result_row(source: str, provider: str, mode: str, answers: dict, threshold: float) -> dict:
    row = {"source": source, "provider": provider}
    if mode in ("noul", "all"):
        for key in LABELS:
            answer = answers.get(key)
            if not isinstance(answer, dict):
                raise JevosError(f"Antwort fehlt: {key}")
            p = _unit(answer.get("noul"), key)
            row[key + "_p"] = round(p, 4)
            row[key + "_yes"] = p >= threshold
    if mode in ("choice", "all"):
        answer = answers.get("category")
        if not isinstance(answer, dict) or answer.get("choice") not in CHOICE["criteria"]:
            raise JevosError("Ungültige Choice-Antwort.")
        probs = answer.get("probabilities")
        if not isinstance(probs, dict) or set(probs) != set(CHOICE["criteria"]):
            raise JevosError("Choice-Wahrscheinlichkeiten fehlen.")
        for key, val in probs.items():
            _unit(val, key)
        row.update({"choice_" + key + "_p": round(float(value), 4) for key, value in probs.items()})
        row["category"] = answer["choice"]
        row["category_confidence"] = round(_unit(answer.get("confidence"), "category"), 4)
    if mode in ("score", "all"):
        answer = answers.get("urgency")
        if not isinstance(answer, dict):
            raise JevosError("Score-Antwort fehlt.")
        score = answer.get("score")
        probs = answer.get("probabilities")
        if (isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 3
                or not isinstance(probs, dict) or set(probs) != {"0", "1", "2", "3"}):
            raise JevosError("Ungültige Score-Antwort.")
        for key, val in probs.items():
            _unit(val, key)
        row.update({"urgency_" + key + "_p": round(float(value), 4) for key, value in probs.items()})
        row["urgency_score"] = round(float(score), 4)
        row["urgency_confidence"] = round(_unit(answer.get("confidence"), "urgency"), 4)
    return row


def pretty_row(row: dict) -> str:
    parts = []
    for key in LABELS:
        if key + "_p" in row:
            parts.append(f"{key}={row[key + '_p']:.2f}{' JA' if row[key + '_yes'] else ''}")
    if "category" in row:
        parts.append(f"Choice={row['category']} (Konfidenz {row['category_confidence']:.2f})")
        parts.append("Optionen " + ", ".join(f"{key}:{row['choice_' + key + '_p']:.2f}" for key in CHOICE["criteria"]))
    if "urgency_score" in row:
        parts.append(f"Score={row['urgency_score']:.2f}/3 (Konfidenz {row['urgency_confidence']:.2f})")
        parts.append("Stufen " + ", ".join(f"{i}:{row['urgency_' + str(i) + '_p']:.2f}" for i in range(4)))
    return f"{row['source']}: " + " | ".join(parts)
