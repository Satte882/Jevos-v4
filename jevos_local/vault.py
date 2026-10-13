"""Obsidian-Markdown ohne Änderungen oder versteckte Ordner lesen."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterator

MAX_FILE_BYTES = 64 * 1024
MAX_TEXT_CHARS = 12_000
MAX_NOTES = 200


def vault_path(value: str | Path) -> Path:
    try:
        path = Path(value).expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise ValueError("Obsidian-Vault-Pfad nicht gefunden oder nicht zugreifbar.") from exc
    if not path.is_dir():
        raise ValueError("Der Obsidian-Vault-Pfad ist kein Ordner.")
    return path


def iter_notes(vault: Path, limit: int = 20) -> Iterator[tuple[str, str]]:
    """Ergibt (relativer Pfad, Text). Kein Lesen außerhalb des Vaults."""
    if not 1 <= limit <= MAX_NOTES:
        raise ValueError(f"--limit muss zwischen 1 und {MAX_NOTES} liegen.")
    vault = vault.resolve()
    count = 0
    for base, dirs, filenames in os.walk(vault, followlinks=False):
        current = Path(base)
        dirs[:] = sorted(
            item for item in dirs
            if not item.startswith(".") and not (current / item).is_symlink()
        )
        for filename in sorted(filenames):
            file_path = current / filename
            if filename.startswith(".") or file_path.suffix.lower() != ".md" or file_path.is_symlink():
                continue
            if not file_path.resolve().is_relative_to(vault):
                continue
            try:
                if file_path.stat().st_size > MAX_FILE_BYTES:
                    continue
                text = file_path.read_text(encoding="utf-8-sig")[:MAX_TEXT_CHARS]
            except (OSError, UnicodeError):
                continue
            if not text.strip():
                continue
            yield file_path.relative_to(vault).as_posix(), text
            count += 1
            if count >= limit:
                return
