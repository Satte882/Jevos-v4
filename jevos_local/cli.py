"""CLI: immer genau einer von zwei Providern; Obsidian nur lesend."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from .client import JevosClient, TypeSafeClient, JevosError
from .decisions import MODES, COLUMNS, questions_for, result_row, pretty_row
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
    p = argparse.ArgumentParser(description="Wähle entweder Jevos (lokal) ODER Jev (Cloud)")
    p.add_argument("--provider", required=True, choices=("local", "jev"))
    p.add_argument("--url", default="http://127.0.0.1:8017", help="Nur lokaler Jevos-Server")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("health")
    for name in ("demo", "vault"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--mode", choices=MODES, default="all")
        cmd.add_argument("--threshold", type=fraction, default=0.75)
        cmd.add_argument("--report", type=Path)
        if name == "vault":
            cmd.add_argument("--vault", required=True)
            cmd.add_argument("--limit", type=positive_limit, default=20)
            cmd.add_argument("--allow-cloud-vault", action="store_true",
                             help="Bestätigung: Notiztexte werden an TypeSafe übertragen")
    return p


def _report(rows: list[dict], filename: Path, excluded_root: Path | None) -> None:
    target = filename.expanduser().resolve()
    if excluded_root and target.is_relative_to(excluded_root.resolve()):
        raise ValueError("CSV-Bericht darf nicht im Obsidian-Vault liegen.")
    if not rows or not set(rows[0]) <= COLUMNS or any(set(row) != set(rows[0]) for row in rows):
        raise ValueError("CSV-Felder nicht erlaubt oder unvollständig.")
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8-sig") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Bericht (ohne Notizinhalte): {target}")


def _run(client, items: list[tuple[str, str]], threshold: float, mode: str, provider: str) -> list[dict]:
    questions = questions_for(mode)
    rows = []
    for name, note in items:
        result = client.ask(note, questions)
        row = result_row(name, provider, mode, result, threshold)
        print(pretty_row(row))
        rows.append(row)
    return rows


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.provider == "jev" and args.url != "http://127.0.0.1:8017":
            raise ValueError("--url ist nur für --provider local erlaubt.")
        if args.command == "vault" and args.provider == "jev" and not args.allow_cloud_vault:
            raise ValueError("Cloud-Vault gesperrt. Freigabe nur mit --allow-cloud-vault.")
        client = JevosClient(base_url=args.url) if args.provider == "local" else TypeSafeClient()
        print("Provider:", "Jevos-v4 LOKAL" if args.provider == "local" else "Jev TYPESAFE CLOUD")
        if args.command == "health":
            print(json.dumps(client.health(), indent=2, ensure_ascii=False))
            return 0
        excluded_root = None
        if args.command == "demo":
            examples = json.loads(EXAMPLES.read_text(encoding="utf-8"))
            items = [(item["id"], item["text"]) for item in examples]
        else:
            excluded_root = vault_path(args.vault)
            if args.report and args.report.expanduser().resolve().is_relative_to(excluded_root):
                raise ValueError("CSV-Bericht darf nicht im Obsidian-Vault liegen.")
            items = list(iter_notes(excluded_root, limit=args.limit))
        if not items:
            print("Keine passenden Markdown-Notizen gefunden.")
            return 0
        rows = _run(client, items, threshold=args.threshold, mode=args.mode, provider=args.provider)
        print(f"Ausgewertet: {len(rows)} | Fragetypen: {args.mode} | Schwelle: {args.threshold:.0%}")
        if args.report:
            _report(rows, args.report, excluded_root)
        return 0
    except (JevosError, ValueError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        return 1
