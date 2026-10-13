import json
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from inbox_assistant.index import VaultIndex, content_text, relevant_excerpt
from inbox_assistant.service import InboxService
from inbox_assistant.store import load
from jevos_local.client import JevosError
from tests import test_inbox
DummyModel = test_inbox.DummyModel


class ReviewTests(unittest.TestCase):
    setUp = test_inbox.InboxTests.setUp
    def test_full_note_and_tail_excerpt(self):
        file = self.inbox / "Test KI.md"
        text = "---\nsource: https://secret.example/urltoken\n---\n\n" + ("Unrelated paragraph.\n\n" * 1000) + "Important transformer architecture and language models."
        file.write_text(text, encoding="utf8")
        self.assertEqual(self.service.note("ZZZZZ_Inbox_noch_Einzuordnen/Test KI.md"), text)
        excerpt = relevant_excerpt(text, "transformer architecture", 700)
        self.assertIn("Important transformer", excerpt)
        self.assertLessEqual(len(excerpt), 700)
        self.assertNotIn("urltoken", content_text(text))

    def test_archive_targets_are_optional_not_manual_targets_removed(self):
        archive = self.vault / "Archiv"
        archive.mkdir()
        (archive / "KI.md").write_text("AI models and testing.", encoding="utf8")
        index = VaultIndex(self.vault, self.inbox)
        note = index.inbox_notes[0]
        self.assertIn("Archiv", index.folders)
        self.assertNotIn("Archiv", [c["folder"] for c in index.candidates(note, {})])
        self.assertIn("Archiv", [c["folder"] for c in index.candidates(note, {"include_archives": True})])

    @patch("inbox_assistant.service.JevosClient")
    def test_reported_references_are_exactly_sent(self, client):
        for name in ("A", "B", "C"):
            (self.vault / "Wissen/KI" / (name + ".md")).write_text("AI models and testing.", encoding="utf8")
        model = DummyModel()
        observed = []
        def ask(text, questions):
            observed.append((text, questions))
            return model.ask(text, questions)
        client.return_value.ask.side_effect = ask
        result = self.service.analyze("local")
        analysis = result["results"][0]["analysis"]
        expected = sorted(r["source"] for c in analysis["evidence"] for r in c["references"])
        self.assertEqual(expected, analysis["reference_sources"])
        self.assertTrue(all(len(c["references"]) <= 2 for c in analysis["evidence"]))
        for candidate in analysis["evidence"]:
            for ref in candidate["references"]:
                self.assertTrue(any(ref["snippet"] in value for value in observed[0][1]["destination"]["criteria"].values()))
        self.assertLessEqual(len(analysis["input_excerpt"]), 1400)

    @patch("inbox_assistant.service.JevosClient")
    def test_failed_retry_removes_previous_approval_and_persists_error(self, client):
        client.return_value = DummyModel()
        self.service.analyze("local")
        source = self.service.index.inbox_notes[0].source
        self.service.decide(source, "approved", "Wissen/KI")
        client.return_value.ask = lambda *args: (_ for _ in ()).throw(JevosError("Timeout test"))
        result = self.service.analyze("local")
        self.assertEqual(result["total"], 0)
        row = self.service.overview()["rows"][0]
        self.assertIsNone(row["analysis"])
        self.assertIsNone(row["decision"])
        self.assertEqual(load(self.service.state_path)["errors"][source]["error"], "Timeout test")

    @patch("inbox_assistant.service.JevosClient")
    def test_background_progress_does_not_block_overview(self, client):
        entered, release = threading.Event(), threading.Event()
        model = DummyModel()
        def ask(text, questions):
            entered.set()
            release.wait(3)
            return model.ask(text, questions)
        client.return_value.ask.side_effect = ask
        self.service.start_analysis("local")
        self.assertTrue(entered.wait(2))
        try:
            self.assertEqual(self.service.overview()["job"]["status"], "running")
            with self.assertRaises(ValueError):
                self.service.start_analysis("local")
            with self.assertRaises(ValueError):
                self.service.prepare()
        finally:
            release.set()
            self.service.analysis_thread.join(3)

    def test_vault_state_paths_are_scoped(self):
        config = self.root / "config-two.json"
        second = self.root / "SecondVault"
        (second / "Inbox").mkdir(parents=True)
        config.write_text(json.dumps({"vault": str(second), "inbox": str(second / "Inbox")}), encoding="utf8")
        one = InboxService(self.root / "config.json")
        two = InboxService(config)
        self.assertNotEqual(one.state_path, two.state_path)

    def test_topic_reference_outweighs_generic_body_vocabulary(self):
        (self.inbox / "Data Mesh Architecture.md").write_text("Data mesh. Business technology platforms and models improve decisions and projects.", encoding="utf8")
        folder = self.vault / "Wissen/KI"
        (folder / "Data Mesh.md").write_text("Domain-owned data products and federated governance.", encoding="utf8")
        for name in ("A", "B", "C"):
            (folder / (name + " Business models.md")).write_text("Business technology platforms and models improve decisions and projects.", encoding="utf8")
        index = VaultIndex(self.vault, self.inbox)
        note = next(n for n in index.inbox_notes if n.title == "Data Mesh Architecture")
        self.assertEqual(index.pick_references("Wissen/KI", note, {})[0].title, "Data Mesh")
