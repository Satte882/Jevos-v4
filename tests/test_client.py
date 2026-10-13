import io
import json
import unittest
from unittest.mock import patch

from jevos_local.client import JevosClient, JevosError


class ClientTests(unittest.TestCase):
    def test_reject_remote_server(self):
        for address in ["https://api.example.org", "http://192.168.1.1:8017",
                        "http://127.0.0.1:8017/x", "http://localhost:8017/?q=1"]:
            with self.subTest(address=address), self.assertRaises(ValueError):
                JevosClient(address)

    @patch("jevos_local.client.urlopen")
    def test_classify_contract(self, mock_open):
        mock_open.return_value = io.BytesIO(json.dumps({
            "model": "jevos-v4",
            "answers": {
                "task": {"type": "noul", "noul": 0.91},
                "idea": {"type": "noul", "noul": 0.18},
                "decision": {"type": "noul", "noul": 0.73}
            }
        }).encode())
        result = JevosClient().classify("Pick a date.")
        self.assertEqual(result, {"task": 0.91, "idea": 0.18, "decision": 0.73})
        request = mock_open.call_args.args[0]
        self.assertEqual(request.get_method(), "POST")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "jev-latest")
        self.assertEqual(len(payload["questions"]), 3)
        self.assertIn("task", payload["questions"])

    @patch("jevos_local.client.urlopen")
    def test_bad_probability_rejected(self, mock_open):
        mock_open.return_value = io.BytesIO(json.dumps({
            "answers": {"task": {"noul": 1.2}, "idea": {"noul": 0.0}, "decision": {"noul": 0.0}}
        }).encode())
        with self.assertRaises(JevosError):
            JevosClient().classify("Test")

    @patch("jevos_local.client.urlopen")
    def test_health_get(self, mock_open):
        mock_open.return_value = io.BytesIO(b'{"status":"ok"}')
        self.assertEqual(JevosClient().health()["status"], "ok")
        self.assertEqual(mock_open.call_args.args[0].get_method(), "GET")

    def test_empty_note_rejected(self):
        with self.assertRaises(ValueError):
            JevosClient().classify("   ")


if __name__ == "__main__":
    unittest.main()
