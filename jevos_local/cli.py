"""CLI für lokale synthetische Tests und Obsidian-Lesemodus."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .client import LABELS, JevosClient, JevosError
from .vault import MAX_NOTES, iter_notes, vault_path

EXAMPLES = Path(__file__).resolve().parent.parent / "examples" / "demo_notes.json"


def fraction(value: str) -> float:
    try:
        number = float(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Eine Zahl zwischen 0 und 1 eingeben.") from exc
    if not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("Der Wert muss zwischen 0 und 1 liegen.")
    return number


def positive_limit(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Eine ganze Zahl von 1 bis {MAX_NOTES} eingeben.") from exc
    if not 1 <= number <= MAX_NOTES:
        raise argparse.ArgumentTypeError(f"Der Wert muss zwischen 1 und {MAX_NOTES} liegen.")
    return number


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Jevos-v4 lokal testen (nur CPU, Obsidian nur lesen)")
    p.add_argument("--url", default="http://127.0.0.1:8017", help="Lokale Jevos-API")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("health", help="Lokalen Modellserver prüfen")
    for name in ("demo", "vault"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--threshold", type=fraction, default=0.75)
        cmd.add_argument("--report", type=Path, help="Lokale CSV (nur Pfade und Bewertungen)")
        if name == "vault":
            cmd.add_argument("--vault", required=True, help="Pfad zum Obsidian-Vault")
            cmd.add_argument("--limit", type=positive_limit, default=20)
    return p


def _report(rows: list[dict], filename: Path, excluded_root: Path | None) -> None:
    target = filename.expanduser().resolve()
    if excluded_root and target.is_relative_to(excluded_root):
        raise ValueError("CSV-Bericht darf nicht im Obsidian-Vault liegen.")
    target.parent.mkdir(parents=True, exist_ok=True)
    columns = ["source"] + [f"{key}_p" for key in LABELS] + [f"{key}_yes" for key in LABELS]
    with target.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Bericht (nur Pfade/Scores): {target}")


def _run(client: JevosClient, items: list[tuple[str, str]], threshold: float) -> list[dict]:
    rows = []
    for name, text in items:
        scores = client.classify(text)
        parts = [f"{key}={scores[key]:.2f}{' JA' if scores[key] >= threshold else ''}" for key in LABELS]
        print(f"{name}: {' | '.join(parts)}")
        row = {"source": name}
        row.update({f"{key}_p": round(scores[key], 4) for key in LABELS})
        row.update({f"{key}_yes": scores[key] >= threshold for key in LABELS})
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        client = JevosClient(base_url=args.url)
        if args.command == "health":
            print(json.dumps(client.health(), indent=2, ensure_ascii=False))
            return 0
        excluded_root = None
        if args.command == "demo":
            examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))
            items = [(item["id"], item["text"]) for item in examples]
        else:
            excluded_root = vault_path(args.vault)
            # Berichtspfad vor dem ersten Modellaufruf prüfen.
            if args.report and args.report.expanduser().resolve().is_relative_to(excluded_root):
                raise ValueError("CSV-Bericht darf nicht im Obsidian-Vault liegen.")
            items = list(iter_notes(excluded_root, limit=args.limit))
        if not items:
            print("Keine passenden Markdown-Notizen gefunden.")
            return 0
        rows = _run(client, items, threshold=args.threshold)
        print(f"Ausgewertet: {len(rows)} | Ja-Schwelle: {args.threshold:.0%}")
        if args.report:
            _report(rows, args.report, excluded_root)
        return 0
    except (JevosError, ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
