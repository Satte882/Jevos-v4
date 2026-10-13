import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jevos_local.client import TypeSafeClient, JevosClient, JevosError
from jevos_local.decisions import questions_for, result_row
from jevos_local.cli import main


class CloudTests(unittest.TestCase):
    def setUp(self):
        self.answer = {
            "task": {"type": "noul", "noul": 0.9},
            "idea": {"type": "noul", "noul": 0.1},
            "decision": {"type": "noul", "noul": 0.2},
            "category": {"type": "choice", "choice": "task", "confidence": 0.9,
                         "probabilities": {"task": 0.9, "idea": 0.02,
                                           "decision": 0.03, "information": 0.05}},
            "urgency": {"type": "score", "score": 1.2, "confidence": 0.6,
                        "probabilities": {"0": 0.1, "1": 0.6, "2": 0.3, "3": 0.0},
                        "legend": {"0": "No action", "1": "Can wait",
                                   "2": "Soon", "3": "Immediately"}}
        }

    def test_all_three_types(self):
        q = questions_for("all")
        self.assertEqual({x["type"] for x in q.values()}, {"noul", "choice", "score"})
        row = result_row("example.md", "jev", "all", self.answer, 0.75)
        self.assertTrue(row["task_yes"])
        self.assertEqual(row["category"], "task")
        self.assertEqual(row["urgency_score"], 1.2)
        self.assertNotIn("content", row)

    def test_key_required(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                TypeSafeClient()

    @patch("jevos_local.client.urlopen")
    def test_cloud_auth_and_correct_endpoint(self, mock_open):
        key = "TEST_SECRET_DO_NOT_LOG"
        mock_open.return_value = io.BytesIO(json.dumps({"answers": self.answer}).encode())
        client = TypeSafeClient(api_key=key)
        answers = client.ask("Remember to buy bread.", questions_for("all"))
        self.assertEqual(answers["category"]["choice"], "task")
        req = mock_open.call_args.args[0]
        self.assertEqual(req.full_url, "https://api.typesafe.ai/v1/systemone")
        self.assertEqual(req.get_header("Authorization"), "Bearer " + key)
        sent = json.loads(req.data)
        self.assertEqual(sent["questions"], questions_for("all"))
        self.assertEqual(sent["model"], "jev-latest")

    def test_local_only_url(self):
        with self.assertRaises(ValueError):
            JevosClient("https://api.typesafe.ai")

    @patch("jevos_local.cli.TypeSafeClient")
    @patch("jevos_local.cli.JevosClient")
    def test_cloud_vault_requires_explicit_consent_without_network(self, local, cloud):
        with tempfile.TemporaryDirectory() as temp:
            Path(temp, "note.md").write_text("Private notes", encoding="utf-8")
            result = main(["--provider", "jev", "vault", "--vault", temp])
        self.assertEqual(result, 1)
        cloud.assert_not_called()
        local.assert_not_called()

    @patch("jevos_local.cli.TypeSafeClient")
    @patch("jevos_local.cli.JevosClient")
    def test_local_demo_never_touches_cloud(self, local, cloud):
        local.return_value.ask.return_value = self.answer
        result = main(["--provider", "local", "demo", "--mode", "all"])
        self.assertEqual(result, 0)
        cloud.assert_not_called()
        self.assertEqual(local.return_value.ask.call_count, 6)

    @patch("jevos_local.cli.TypeSafeClient")
    @patch("jevos_local.cli.JevosClient")
    def test_cloud_demo_never_touches_local(self, local, cloud):
        cloud.return_value.ask.return_value = self.answer
        result = main(["--provider", "jev", "demo", "--mode", "all"])
        self.assertEqual(result, 0)
        local.assert_not_called()
        self.assertEqual(cloud.return_value.ask.call_count, 6)


if __name__ == "__main__":
    unittest.main()
