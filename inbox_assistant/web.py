"""Lokale UI über Python-Standardbibliothek. Nur 127.0.0.1, Token gegen CSRF."""
from __future__ import annotations

import argparse
import json
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .service import InboxService

HTML = Path(__file__).with_name("ui.html")


def handler_factory(service: InboxService, token: str):
    class Handler(BaseHTTPRequestHandler):
        def _valid_host(self) -> bool:
            return self.headers.get("Host", "") in ("127.0.0.1:8765", "localhost:8765")

        def _token_ok(self) -> bool:
            return self.headers.get("X-Session-Token", "") == token

        def _send(self, status: int, value: dict, *, body: bytes | None = None,
                  mime: str = "application/json; charset=utf-8"):
            content = body if body is not None else json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", mime)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if not self._valid_host():
                return self._send(403, {"error": "Ungültiger Host."})
            parsed = urlsplit(self.path)
            if parsed.path == "/":
                page = HTML.read_text(encoding="utf-8").replace("__SESSION_TOKEN__", token)
                return self._send(200, {}, body=page.encode("utf-8"), mime="text/html; charset=utf-8")
            if not self._token_ok():
                return self._send(403, {"error": "Session-Token fehlt."})
            query = parse_qs(parsed.query)
            try:
                if parsed.path == "/api/state":
                    result = service.overview()
                elif parsed.path == "/api/note":
                    result = {"text": service.note(query.get("source", [""])[0])}
                elif parsed.path == "/api/references":
                    result = {"references": service.references(query.get("folder", [""])[0])}
                else:
                    return self._send(404, {"error": "Unbekannte Anfrage."})
                return self._send(200, result)
            except (ValueError, OSError) as exc:
                return self._send(400, {"error": str(exc)})

        def do_POST(self):
            if not self._valid_host() or not self._token_ok():
                return self._send(403, {"error": "Nicht autorisiert."})
            if self.headers.get("Origin") not in (None, "http://127.0.0.1:8765", "http://localhost:8765"):
                return self._send(403, {"error": "Fremder Origin blockiert."})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self._send(415, {"error": "Nur JSON erlaubt."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 16000:
                    raise ValueError("Ungültige Anfragelänge.")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("JSON-Objekt erforderlich.")
                if self.path == "/api/analyze":
                    result = service.analyze(
                        payload.get("provider", ""),
                        cloud_consent=payload.get("cloud_consent") is True,
                        limit=payload.get("limit", 20),
                    )
                elif self.path == "/api/decide":
                    result = service.decide(payload.get("source", ""),
                                            payload.get("status", ""),
                                            payload.get("destination"))
                elif self.path == "/api/reference":
                    result = service.reference_action(payload.get("folder", ""),
                                                       payload.get("source", ""),
                                                       payload.get("action", ""))
                elif self.path == "/api/cancel":
                    if payload.get("confirm") != "CANCEL":
                        raise ValueError("Ausdrückliche Abbruchbestätigung fehlt.")
                    result = service.cancel_pending()
                elif self.path == "/api/prepare":
                    if payload.get("confirm") != "PREPARE":
                        raise ValueError("Separate Freigabe für Sicherung/Stapel fehlt.")
                    plan = service.prepare()
                    result = {"batch_id": plan["batch_id"], "backup": plan["backup"],
                              "moves": [{"source": m["source"], "target": m["target"]}
                                        for m in plan["moves"]]}
                else:
                    return self._send(404, {"error": "Unbekannte Anfrage."})
                return self._send(200, result)
            except (ValueError, OSError, KeyError, json.JSONDecodeError, RuntimeError) as exc:
                return self._send(400, {"error": str(exc)})

        def log_message(self, format, *args):
            # Keine Quellpfade oder Note-Texte in Serverzugriffslogs.
            pass
    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Obsidian Inbox-Assistent – lokales Dashboard")
    parser.add_argument("--config", default=None,
                        help="Optional lokale config.json statt config.example.json")
    args = parser.parse_args(argv)
    try:
        service = InboxService(args.config)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Start fehlgeschlagen: {exc}", file=sys.stderr)
        return 1
    token = secrets.token_urlsafe(32)
    with ThreadingHTTPServer(("127.0.0.1", 8765), handler_factory(service, token)) as server:
        print("Obsidian Inbox-Assistent: http://127.0.0.1:8765")
        print("Nur lokaler Zugriff. Beenden mit Strg+C.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
