import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from inbox_assistant.index import VaultIndex, safe_path
from inbox_assistant.bridge import bridge_status
from inbox_assistant.service import InboxService


class DummyModel:
    calls = 0
    def ask(self, text, questions):
        self.calls += 1
        keys = list(questions["destination"]["criteria"])
        first = keys[0]
        probs = {key: (0.9 if key == first else 0.1 / (len(keys)-1)) for key in keys}
        return {"destination": {"type": "choice", "choice": first,
                                "confidence": 0.8, "probabilities": probs}}


class InboxTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.vault = self.root / "Obsidian"
        self.inbox = self.vault / "ZZZZZ_Inbox_noch_Einzuordnen"
        self.inbox.mkdir(parents=True)
        (self.vault / "Wissen" / "KI").mkdir(parents=True)
        (self.vault / "Privat").mkdir()
        (self.vault / ".obsidian").mkdir()
        (self.inbox / "Test KI.md").write_text("Compare language models and choose one.", encoding="utf8")
        (self.vault / "Wissen" / "KI" / "KI-Beispiel.md").write_text("AI models and testing.", encoding="utf8")
        (self.vault / "Privat" / "Sport.md").write_text("Running and exercise.", encoding="utf8")
        (self.vault / ".obsidian" / "secret.md").write_text("hidden", encoding="utf8")
        config = self.root / "config.json"
        config.write_text(json.dumps({"vault": str(self.vault), "inbox": str(self.inbox)}), encoding="utf8")
        self.service = InboxService(config)
        self.service.workdir = self.root / "app-state"
        self.service.state_path = self.service.workdir / "state.json"
        self.service.bridge_dir = self.service.workdir / "bridge"
        self.service.backup_dir = self.service.workdir / "backups"

    def test_read_only_scan_and_candidates(self):
        idx = VaultIndex(self.vault, self.inbox)
        self.assertEqual(len(idx.inbox_notes), 1)
        self.assertIn("Wissen/KI", idx.folders)
        self.assertNotIn(".obsidian", idx.folders)
        self.assertEqual(idx.candidates(idx.inbox_notes[0], self.service.state)[0]["folder"], "Wissen/KI")

    def test_safe_paths(self):
        with self.assertRaises(ValueError):
            safe_path(self.vault, "../somewhere", exists=False)
        with self.assertRaises(ValueError):
            safe_path(self.vault, "/etc/passwd", exists=False)

    @patch("inbox_assistant.service.TypeSafeClient")
    @patch("inbox_assistant.service.JevosClient")
    def test_explicit_local_and_cloud_consent(self, local, cloud):
        local.return_value = DummyModel()
        result = self.service.analyze("local")
        self.assertEqual(result["total"], 1)
        cloud.assert_not_called()
        with self.assertRaises(ValueError):
            self.service.analyze("jev")
        cloud.assert_not_called()
        cloud.return_value = DummyModel()
        self.service.analyze("jev", cloud_consent=True)
        self.assertEqual(cloud.call_count, 1)

    @patch("inbox_assistant.service.JevosClient")
    def test_two_stage_move_with_backup_and_no_touch_of_vault(self, local):
        local.return_value = DummyModel()
        self.service.analyze("local")
        note = self.service.index.inbox_notes[0]
        self.service.decide(note.source, "approved", "Wissen/KI")
        plan = self.service.prepare()
        self.assertEqual(plan["moves"][0]["source"], note.source)
        self.assertTrue(Path(plan["backup"]["path"]).exists())
        self.assertTrue((self.inbox / "Test KI.md").exists())
        self.assertFalse((self.vault / "Wissen" / "KI" / "Test KI.md").exists())
        self.assertEqual(bridge_status(self.service.bridge_dir)["status"], "awaiting-obsidian")
        with self.assertRaises(ValueError):
            self.service.analyze("local")
        with self.assertRaises(ValueError):
            self.service.decide(note.source, "deferred")

    @patch("inbox_assistant.service.JevosClient")
    def test_changed_note_prevents_move(self, local):
        local.return_value = DummyModel()
        self.service.analyze("local")
        note = self.service.index.inbox_notes[0]
        self.service.decide(note.source, "approved", "Wissen/KI")
        (self.inbox / "Test KI.md").write_text("Content changed!", encoding="utf8")
        with self.assertRaises(ValueError):
            self.service.prepare()
        self.assertFalse((self.service.bridge_dir / "pending.json").exists())

    @patch("inbox_assistant.service.JevosClient")
    def test_file_collision_prevents_move(self, local):
        local.return_value = DummyModel()
        self.service.analyze("local")
        note = self.service.index.inbox_notes[0]
        self.service.decide(note.source, "approved", "Wissen/KI")
        (self.vault / "Wissen" / "KI" / "Test KI.md").write_text("Do not overwrite", encoding="utf8")
        with self.assertRaises(ValueError):
            self.service.prepare()
        self.assertEqual((self.vault / "Wissen" / "KI" / "Test KI.md").read_text(), "Do not overwrite")

    def test_corrections_persist_and_invalidate_predictions(self):
        refs = self.service.references("Wissen/KI")
        self.assertEqual(len(refs), 1)
        source = refs[0]["source"]
        self.service.reference_action("Wissen/KI", source, "pin")
        self.assertEqual(self.service.state["pinned_references"]["Wissen/KI"], [source])
        self.service.reference_action("Wissen/KI", source, "exclude")
        self.assertIn(source, self.service.state["excluded_references"])


if __name__ == "__main__":
    unittest.main()
