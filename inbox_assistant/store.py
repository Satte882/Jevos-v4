"""Lokal gespeicherte Prüfergebnisse und atomare Statusänderungen."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def load(path: Path) -> dict:
    if not path.exists():
        return {"analyses": {}, "decisions": {}, "errors": {}, "excluded_references": [], "pinned_references": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Ungültiger lokaler Status.")
    for key, default in (("analyses", {}), ("decisions", {}),
                         ("errors", {}), ("excluded_references", []), ("pinned_references", {})):
        data.setdefault(key, default)
    return data


def atomic_json(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".tmp-", suffix=".json", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(value, out, ensure_ascii=False, indent=2)
            out.flush()
            os.fsync(out.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
