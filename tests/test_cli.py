import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jevos_local.cli import main, positive_limit, fraction, _report


class CliTests(unittest.TestCase):
    def test_inputs(self):
        self.assertEqual(positive_limit("20"), 20)
        self.assertEqual(fraction("0.75"), 0.75)
        for bad in ("-1", "201", "abc"):
            with self.assertRaises(Exception):
                positive_limit(bad)

    def test_report_refuses_vault(self):
        with tempfile.TemporaryDirectory() as tmp:
            vault = Path(tmp)
            with self.assertRaises(ValueError):
                _report([], vault / "results.csv", vault)
            self.assertFalse((vault / "results.csv").exists())

    def test_report_only_paths_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "reports" / "r.csv"
            rows = [{
                "source": "hello.md", "task_p": 0.9, "idea_p": 0.1,
                "decision_p": 0.2, "task_yes": True, "idea_yes": False,
                "decision_yes": False
            }]
            _report(rows, output, None)
            with output.open(encoding="utf-8-sig", newline="") as f:
                data = list(csv.DictReader(f))
            self.assertEqual(data[0]["source"], "hello.md")
            self.assertNotIn("content", data[0])

    @patch("jevos_local.cli.JevosClient")
    def test_demo(self, client_type):
        client_type.return_value.ask.return_value = {
            "task": {"type": "noul", "noul": 0.88},
            "idea": {"type": "noul", "noul": 0.05},
            "decision": {"type": "noul", "noul": 0.1},
        }
        self.assertEqual(main(["--provider", "local", "demo", "--mode", "noul"]), 0)
        self.assertEqual(client_type.return_value.ask.call_count, 6)

    @patch("jevos_local.cli.JevosClient")
    def test_vault_reads_without_write(self, client_type):
        client_type.return_value.ask.return_value = {
            "task": {"type": "noul", "noul": 0.8},
            "idea": {"type": "noul", "noul": 0.1},
            "decision": {"type": "noul", "noul": 0.2},
        }
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            note = root / "notiz.md"
            note.write_text("A note", encoding="utf-8")
            self.assertEqual(main(["--provider", "local", "vault", "--vault", str(root), "--limit", "1", "--mode", "noul"]), 0)
            self.assertEqual(note.read_text(encoding="utf-8"), "A note")
            self.assertEqual(list(root.iterdir()), [note])


if __name__ == "__main__":
    unittest.main()
