"""Minimaler Client für die lokale, Jev-kompatible Jevos-v4-API."""
from __future__ import annotations

import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

QUESTIONS = {
    "task": {
        "type": "noul",
        "instructions": "Does this note describe a specific actionable task someone should complete?",
    },
    "idea": {
        "type": "noul",
        "instructions": "Does this note describe an idea for a possible future activity or project?",
    },
    "decision": {
        "type": "noul",
        "instructions": "Does this note describe a decision or choice that still needs to be made?",
    },
}
LABELS = tuple(QUESTIONS)


class JevosError(RuntimeError):
    """Unerwartete Antwort oder fehlender lokaler Modellserver."""


class JevosClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8017", timeout: int = 30):
        parsed = urlsplit(base_url)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in ("127.0.0.1", "localhost", "::1")
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in ("", "/")
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Nur eine lokale HTTP-Adresse (localhost / 127.0.0.1) ist erlaubt.")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, endpoint: str, payload: dict | None = None) -> dict:
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {"Accept": "application/json"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        api_key = os.environ.get("JEV_API_KEY")
        if api_key:
            headers["Authorization"] = "Bearer " + api_key
        req = Request(
            self.base_url + endpoint,
            data=body,
            headers=headers,
            method="POST" if payload is not None else "GET",
        )
        try:
            with urlopen(req, timeout=self.timeout) as res:
                content = res.read()
        except HTTPError as exc:
            raise JevosError(f"Lokaler Jevos-Server hat die Anfrage abgelehnt (HTTP {exc.code}).") from exc
        except TimeoutError as exc:
            raise JevosError(f"Zeitlimit: Das lokale Modell hat nach {self.timeout} Sekunden nicht geantwortet.") from exc
        except (URLError, OSError) as exc:
            raise JevosError(
                "Lokaler Jevos-Server nicht erreichbar oder Anfrage abgelehnt. "
                "Prüfe scripts/start-jev.ps1 und http://127.0.0.1:8017/health."
            ) from exc
        try:
            result = json.loads(content)
        except (ValueError, UnicodeDecodeError) as exc:
            raise JevosError("Antwort des lokalen Servers ist kein gültiges JSON.") from exc
        if not isinstance(result, dict):
            raise JevosError("Unerwartetes API-Antwortformat (Objekt erwartet).")
        return result

    def health(self) -> dict:
        return self._request("/health")

    def ask(self, note: str, questions: dict) -> dict:
        """Beliebige Jev-Entscheidungstypen in EINER Anfrage beantworten."""
        if not isinstance(note, str) or not note.strip():
            raise ValueError("Der Text darf nicht leer sein.")
        if not isinstance(questions, dict) or not questions:
            raise ValueError("Mindestens eine Frage ist erforderlich.")
        result = self._request(
            "/v1/systemone",
            {"model": "jev-latest", "state": note, "questions": questions},
        )
        answers = result.get("answers")
        if not isinstance(answers, dict) or any(
            not isinstance(answers.get(name), dict) for name in questions
        ):
            raise JevosError("Unvollständige API-Antwort ('answers').")
        return answers

    def classify(self, note: str) -> dict[str, float]:
        if not isinstance(note, str) or not note.strip():
            raise ValueError("Der Text darf nicht leer sein.")
        result = self._request(
            "/v1/systemone",
            {"model": "jev-latest", "state": note, "questions": QUESTIONS},
        )
        answers = result.get("answers")
        if not isinstance(answers, dict):
            raise JevosError("Antwort ohne 'answers'-Objekt.")
        probabilities = {}
        for name in LABELS:
            answer = answers.get(name)
            if not isinstance(answer, dict):
                raise JevosError(f"Keine Antwort für '{name}'.")
            number = answer.get("noul")
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not 0 <= number <= 1:
                raise JevosError(f"Ungültige Wahrscheinlichkeit für '{name}'.")
            probabilities[name] = float(number)
        return probabilities


class TypeSafeClient(JevosClient):
    """Offizielle Jev-Cloud-API; feste URL, kein lokaler Fallback."""

    def __init__(self, api_key: str | None = None, timeout: int = 30):
        self.base_url = "https://api.typesafe.ai"
        self.timeout = timeout
        self.api_key = api_key if api_key is not None else os.environ.get("TYPESAFE_API_KEY", "")
        if not self.api_key or not self.api_key.strip():
            raise ValueError(
                "TYPESAFE_API_KEY fehlt. Den Schlüssel nur lokal als "
                "Umgebungsvariable setzen oder scripts/run.ps1 verwenden."
            )

    def _request(self, endpoint: str, payload: dict | None = None) -> dict:
        if endpoint not in ("/v1/systemone", "/v1/models"):
            raise JevosError("Nicht unterstützter TypeSafe-API-Pfad.")
        body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self.api_key,
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
        request = Request(
            self.base_url + endpoint, data=body, headers=headers,
            method="POST" if payload is not None else "GET",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                content = response.read()
        except HTTPError as exc:
            # Nie den Response-Body ausgeben: Er könnte vertrauliche Nutzerdaten enthalten.
            raise JevosError(f"TypeSafe API: HTTP {exc.code} (Berechtigung, Guthaben oder Anfrage prüfen).") from None
        except (URLError, TimeoutError, OSError):
            raise JevosError("TypeSafe API ist nicht erreichbar (Netzwerk/Timeout).") from None
        try:
            result = json.loads(content)
        except (ValueError, UnicodeDecodeError):
            raise JevosError("TypeSafe lieferte kein gültiges JSON.") from None
        if not isinstance(result, dict):
            raise JevosError("Unerwartetes TypeSafe-Antwortformat.")
        return result

    def health(self) -> dict:
        """GET /v1/models ist der dokumentierte Cloud-Check (mit Authentifizierung)."""
        return self._request("/v1/models")
