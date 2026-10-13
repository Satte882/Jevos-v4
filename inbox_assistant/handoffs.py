"""Kurzlebige Einmal-Übergaben: ausschließlich RAM, niemals Klartextdateien."""
import secrets
import threading
import time

from redaction_app.core import MAX_TEXT_CHARS


class RedactionHandoffs:
    def __init__(self, clock=time.monotonic, ttl=300, capacity=20):
        self.clock, self.ttl, self.capacity = clock, ttl, capacity
        self.items = {}
        self.lock = threading.Lock()

    def _expire(self):
        now = self.clock()
        self.items = {key: item for key, item in self.items.items() if item[0] > now}

    def create(self, text, title, kind):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Bitte einen nicht leeren Text übergeben.")
        if len(text) > MAX_TEXT_CHARS:
            raise ValueError("Maximal 100.000 Zeichen sind erlaubt.")
        if not isinstance(title, str) or not title.strip() or len(title) > 500:
            raise ValueError("Ungültiger Notiztitel.")
        if kind not in ("selection", "note"):
            raise ValueError("Ungültige Auswahlart.")
        with self.lock:
            self._expire()
            if len(self.items) >= self.capacity:
                raise ValueError("Zu viele offene Übergaben; bitte bestehende Ansichten öffnen oder fünf Minuten warten.")
            key = secrets.token_hex(32)
            self.items[key] = (self.clock() + self.ttl, {"text": text, "title": title, "kind": kind})
            timer = threading.Timer(self.ttl, self._discard, args=(key,))
            timer.daemon = True
            timer.start()
            return {"handoff_id": key, "expires_in": self.ttl}

    def _discard(self, key):
        with self.lock:
            self.items.pop(key, None)

    def consume(self, key):
        with self.lock:
            self._expire()
            if not isinstance(key, str) or key not in self.items:
                raise ValueError("Übergabe abgelaufen oder bereits übernommen. Bitte erneut aus Obsidian starten.")
            return self.items.pop(key)[1]
