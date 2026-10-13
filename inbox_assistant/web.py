"""Lokale UI über Python-Standardbibliothek. Nur 127.0.0.1, Token gegen CSRF."""
from __future__ import annotations

import argparse
import base64
import binascii
import json
import secrets
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from .service import InboxService
from .handoffs import RedactionHandoffs
from redaction_app.core import redact
from redaction_app.docx import extract_docx

HTML = Path(__file__).with_name("ui.html")
REDACTION_HTML = Path(__file__).resolve().parent.parent / "redaction_app" / "ui.html"
UI_CSS = Path(__file__).with_name("assets") / "ui.css"
FAVICON = Path(__file__).with_name("assets") / "favicon.svg"


def handler_factory(service: InboxService, token: str):
    handoffs = RedactionHandoffs()
    class Handler(BaseHTTPRequestHandler):
        def _local_origin(self):
            return (self.headers.get("Origin") in (None, "http://127.0.0.1:8765", "http://localhost:8765")
                    and self.headers.get("Sec-Fetch-Site") not in ("cross-site", "same-site"))
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
            self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self'; base-uri 'none'; frame-ancestors 'none'")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if not self._valid_host():
                return self._send(403, {"error": "Ungültiger Host."})
            parsed = urlsplit(self.path)
            if parsed.path == "/api/plugin-context":
                if not self._local_origin():
                    return self._send(403, {"error": "Fremder Origin blockiert."})
                return self._send(200, {"protocol": 2, "token": token,
                                        "vault": str(service.index.root), "inbox": service.index.inbox_rel})
            if parsed.path == "/assets/ui.css":
                return self._send(200, {}, body=UI_CSS.read_bytes(), mime="text/css; charset=utf-8")
            if parsed.path == "/favicon.svg":
                return self._send(200, {}, body=FAVICON.read_bytes(), mime="image/svg+xml")
            if parsed.path in ("/", "/anonymize"):
                template = HTML if parsed.path == "/" else REDACTION_HTML
                page = template.read_text(encoding="utf-8").replace("__SESSION_TOKEN__", token)
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
            if not self._local_origin():
                return self._send(403, {"error": "Fremder Origin blockiert."})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self._send(415, {"error": "Nur JSON erlaubt."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                allowed_size = 3_000_000 if self.path in ("/api/redact", "/api/docx-text", "/api/handoffs/redaction") else 16000
                if not 0 < length <= allowed_size:
                    raise ValueError("Ungültige Anfragelänge.")
                payload = json.loads(self.rfile.read(length))
                if not isinstance(payload, dict):
                    raise ValueError("JSON-Objekt erforderlich.")
                if self.path == "/api/handoffs/redaction":
                    result = handoffs.create(payload.get("text"), payload.get("title"), payload.get("kind"))
                elif self.path == "/api/handoffs/redaction/consume":
                    result = handoffs.consume(payload.get("handoff_id"))
                elif self.path == "/api/redact":
                    result = redact(payload.get("text"))
                elif self.path == "/api/docx-text":
                    if not isinstance(payload.get("filename"), str) or not payload["filename"].lower().endswith(".docx"):
                        raise ValueError("Nur .docx-Dateien zugelassen.")
                    raw = payload.get("data")
                    if not isinstance(raw, str):
                        raise ValueError("DOCX-Daten fehlen.")
                    try:
                        data = base64.b64decode(raw, validate=True)
                    except (ValueError, binascii.Error) as exc:
                        raise ValueError("Ungültige DOCX-Kodierung.") from exc
                    result = {"text": extract_docx(data)}
                elif self.path == "/api/analyze":
                    result = service.start_analysis(
                        payload.get("provider", ""),
                        cloud_consent=payload.get("cloud_consent") is True,
                        limit=payload.get("limit", 20),
                        include_archives=payload.get("include_archives") is True,
                        source=payload.get("source"),
                        expected_sha256=payload.get("expected_sha256"),
                    )
                elif self.path == "/api/decide":
                    result = service.decide(payload.get("source", ""),
                                            payload.get("status", ""),
                                            payload.get("destination"), payload.get("expected_sha256"))
                elif self.path == "/api/reference":
                    result = service.reference_action(payload.get("folder", ""),
                                                       payload.get("source", ""),
                                                       payload.get("action", ""))
                elif self.path == "/api/cancel":
                    if payload.get("confirm") != "CANCEL":
                        raise ValueError("Ausdrückliche Abbruchbestätigung fehlt.")
                    result = service.cancel_pending(payload.get("batch_id"))
                elif self.path == "/api/prepare":
                    if payload.get("confirm") != "PREPARE":
                        raise ValueError("Separate Freigabe für Sicherung/Stapel fehlt.")
                    plan = service.prepare(payload.get("source"), payload.get("expected_sha256"))
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
        local_config = Path(__file__).resolve().parent.parent / "config.json"
        config = args.config or (local_config if local_config.exists() else None)
        service = InboxService(config)
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
