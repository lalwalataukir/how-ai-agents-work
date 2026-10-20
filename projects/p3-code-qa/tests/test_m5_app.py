"""Milestone 5: a web app with limits"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: Claude is faked
sys.path.insert(0, str(Path(__file__).parent.parent))
from fastapi.testclient import TestClient  # noqa: E402

import app  # noqa: E402
import qa  # noqa: E402

HINT = ("check_limits is E9's: a deque of times per visitor, a 429 at MAX_PER_MINUTE, and a 503 when spent[\"dollars\"] "
        "reaches DAILY_BUDGET. ask loops over qa.steps(body.question, index()), adds the done event's cost to "
        "spent[\"dollars\"], and yields every event.")
EVENTS = [{"type": "tool", "name": "search_code", "input": {"query": "login"}},
          {"type": "done", "answer": "It locks after 5 tries [tinyshop/auth.py:31-35].", "citations": [], "warnings": [],
           "calls": 2, "cost": 0.0012}]


def events_from(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]


class AppTest(unittest.TestCase):
    def setUp(self):
        app.recent.clear()
        app.spent.update(day="", dollars=0.0)
        for patch in (mock.patch.object(qa, "steps", lambda question, index: iter([dict(e) for e in EVENTS])),
                      mock.patch.object(app, "index", lambda: None)):
            patch.start()
            self.addCleanup(patch.stop)
        self.client = TestClient(app.app)

    def test_the_page_and_health(self):
        self.assertIn("Ask the codebase", self.client.get("/").text)
        self.assertEqual(self.client.get("/health").json(), {"ok": True})

    def test_events_stream_in_order_and_the_cost_is_counted(self):
        response = self.client.post("/ask", json={"question": "How does login lock?"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        events = events_from(response)
        self.assertEqual([e["type"] for e in events], ["tool", "done"])
        self.assertIn("seconds", events[-1])
        self.assertAlmostEqual(app.spent["dollars"], 0.0012)

    def test_bad_questions_are_turned_away(self):
        self.assertEqual(self.client.post("/ask", json={"question": "hi"}).status_code, 422)
        self.assertEqual(self.client.post("/ask", json={"question": "x" * 501}).status_code, 422)

    def test_too_many_questions_get_a_429(self):
        codes = [self.client.post("/ask", json={"question": "How does login lock?"}).status_code for _ in range(app.MAX_PER_MINUTE + 1)]
        self.assertEqual(codes, [200] * app.MAX_PER_MINUTE + [429])

    def test_an_empty_budget_gets_a_503(self):
        self.client.post("/ask", json={"question": "How does login lock?"})
        app.spent["dollars"] = app.DAILY_BUDGET
        response = self.client.post("/ask", json={"question": "How does login lock?"})
        self.assertEqual((response.status_code, response.json()["detail"]), (503, "Today's budget is used up. Try again tomorrow."))


if __name__ == "__main__":
    unittest.main()
