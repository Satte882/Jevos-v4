import json
import unittest
from pathlib import Path
from unittest.mock import patch
from tests import test_inbox
from inbox_assistant.handoffs import RedactionHandoffs
from inbox_assistant.bridge import bridge_status


class SingleNoteTests(unittest.TestCase):
    setUp = test_inbox.InboxTests.setUp

    def second_note(self):
        file = self.inbox / "Zweite.md"
        file.write_text("Sports and running.", encoding="utf8")
        return "ZZZZZ_Inbox_noch_Einzuordnen/Zweite.md"

    @patch("inbox_assistant.service.JevosClient")
    def test_single_analysis_preserves_other_results_and_decisions(self, client):
        client.return_value = test_inbox.DummyModel()
        other = self.second_note()
        self.service.analyze("local")
        self.service.decide(other, "approved", "Privat")
        old = json.dumps(self.service.state["analyses"][other], sort_keys=True)
        result = self.service.analyze("local", source="ZZZZZ_Inbox_noch_Einzuordnen/Test KI.md")
        self.assertEqual(result["total"], 1)
        self.assertEqual(old, json.dumps(self.service.state["analyses"][other], sort_keys=True))
        self.assertEqual(self.service.state["decisions"][other]["status"], "approved")

    @patch("inbox_assistant.service.JevosClient")
    def test_single_plan_and_scoped_cancel_keep_backup(self, client):
        client.return_value = test_inbox.DummyModel()
        other = self.second_note()
        self.service.analyze("local")
        one = "ZZZZZ_Inbox_noch_Einzuordnen/Test KI.md"
        self.service.decide(one, "approved", "Wissen/KI")
        self.service.decide(other, "approved", "Privat")
        plan = self.service.prepare(source=one)
        self.assertEqual([one], [m["source"] for m in plan["moves"]])
        self.assertEqual(self.service.state["decisions"][other]["status"], "approved")
        with self.assertRaises(ValueError): self.service.cancel_pending("wrong-id")
        self.service.cancel_pending(plan["batch_id"])
        self.assertEqual(bridge_status(self.service.bridge_dir)["status"], "none")
        self.assertTrue(Path(plan["backup"]["path"]).exists())
        self.assertTrue((self.inbox / "Test KI.md").exists())

    @patch("inbox_assistant.service.JevosClient")
    def test_invalid_source_and_changed_snapshot_do_not_start(self, client):
        for source in ("", [], "../bad.md", "Wissen/KI/KI-Beispiel.md"):
            with self.assertRaises((ValueError, OSError)):
                self.service.start_analysis("local", source=source)
        with self.assertRaises(ValueError):
            self.service.start_analysis("local", source="ZZZZZ_Inbox_noch_Einzuordnen/Test KI.md", expected_sha256="wrong")
        self.assertFalse(self.service.busy)
        client.assert_not_called()


class HandoffTests(unittest.TestCase):
    def test_one_use_expiration_and_independent_requests(self):
        now = [10]
        store = RedactionHandoffs(clock=lambda: now[0])
        a = store.create("Alice private", "A", "selection")
        b = store.create("Bob private", "B", "note")
        self.assertNotIn("Alice", a["handoff_id"])
        self.assertEqual(store.consume(a["handoff_id"])["text"], "Alice private")
        with self.assertRaises(ValueError): store.consume(a["handoff_id"])
        now[0] = 310
        with self.assertRaises(ValueError): store.consume(b["handoff_id"])
        self.assertEqual(store.items, {})


class PluginHttpTests(unittest.TestCase):
    def setUp(self):
        import threading
        from http.server import ThreadingHTTPServer
        from inbox_assistant.web import handler_factory
        test_inbox.InboxTests.setUp(self)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler_factory(self.service, "test-session"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.shutdown)

    def shutdown(self):
        self.server.shutdown(); self.server.server_close(); self.thread.join()

    def request(self, route, payload=None, extra=None):
        import http.client
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port)
        headers = {"Host": "127.0.0.1:8765", "X-Session-Token": "test-session", "Content-Type": "application/json"}
        headers.update(extra or {})
        connection.request("GET" if payload is None else "POST", route,
                           None if payload is None else json.dumps(payload), headers)
        response = connection.getresponse()
        result = (response.status, json.loads(response.read()))
        connection.close()
        return result

    def test_bootstrap_and_handoffs_require_local_origin_and_token(self):
        status, context = self.request("/api/plugin-context")
        self.assertEqual(status, 200)
        self.assertEqual(context["protocol"], 2)
        for headers in ({"Origin": "https://evil.example"}, {"Sec-Fetch-Site": "cross-site"}, {"Host": "evil.example"}):
            self.assertEqual(self.request("/api/plugin-context", extra=headers)[0], 403)
        payload = {"text": "Private Alice text", "title": "Test", "kind": "selection"}
        self.assertEqual(self.request("/api/handoffs/redaction", payload, {"X-Session-Token": "bad"})[0], 403)
        status, handoff = self.request("/api/handoffs/redaction", payload)
        self.assertEqual(status, 200)
        self.assertEqual(set(handoff), {"handoff_id", "expires_in"})
        status, received = self.request("/api/handoffs/redaction/consume", {"handoff_id": handoff["handoff_id"]})
        self.assertEqual(status, 200)
        self.assertEqual(received, payload)
        self.assertEqual(self.request("/api/handoffs/redaction/consume", {"handoff_id": handoff["handoff_id"]})[0], 400)

    @patch("inbox_assistant.service.JevosClient")
    def test_http_single_note_analysis(self, model):
        model.return_value = test_inbox.DummyModel()
        status, started = self.request("/api/analyze", {"provider": "local", "source": "ZZZZZ_Inbox_noch_Einzuordnen/Test KI.md"})
        self.assertEqual(status, 200)
        self.service.analysis_thread.join(3)
        status, state = self.request("/api/state")
        self.assertEqual(state["job"]["id"], started["job_id"])
        self.assertEqual(state["job"]["status"], "finished")

    def test_limits_and_validation(self):
        store = RedactionHandoffs(capacity=1)
        for text,title,kind in [(" ","A","note"),("x"*100001,"A","note"),("x","","note"),("x","A","bad")]:
            with self.assertRaises(ValueError): store.create(text,title,kind)
        store.create("x","A","note")
        with self.assertRaises(ValueError): store.create("y","B","note")

    def test_timer_removes_plaintext_without_another_request(self):
        import time
        store = RedactionHandoffs(ttl=0.02)
        store.create("private","A","note")
        time.sleep(0.08)
        self.assertEqual(store.items, {})
