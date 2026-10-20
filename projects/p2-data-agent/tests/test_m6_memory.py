"""Milestone 6: follow-up questions"""
import io
import os
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: Claude is faked
sys.path.insert(0, str(Path(__file__).parent.parent))
import analyst  # noqa: E402
from fakes import FakeClaude, answer, calls, sql, test_db  # noqa: E402

HINT = ("Append two messages to self.memory: the question as \"user\", and the answer plus the last 3 queries in "
        "<sql> tags as \"assistant\". Then keep self.memory[-2 * MAX_TURNS:], so old turns drop off and cost stays flat.")
TOTAL = "SELECT SUM(i.quantity * i.unit_cents) / 100.0 FROM order_items i JOIN orders o ON o.id = i.order_id WHERE o.status = 'completed'"


class MemoryTest(unittest.TestCase):
    def test_a_follow_up_sees_the_last_answer_and_its_sql(self):
        fake = FakeClaude(calls(sql(TOTAL)), answer("Revenue was $124,123.45.", 124123.45),
                          answer("By region: ...", None))
        session = analyst.Session(test_db())
        with mock.patch.object(analyst, "client", fake), redirect_stderr(io.StringIO()):
            session.ask("What was total revenue?")
            session.ask("Now split that by region")
        follow_up = fake.requests[2]["messages"]
        self.assertEqual(follow_up[0], {"role": "user", "content": "What was total revenue?"})
        self.assertEqual(follow_up[1]["role"], "assistant")
        self.assertIn("Revenue was $124,123.45.", follow_up[1]["content"])
        self.assertIn(f"<sql>\n{TOTAL}\n</sql>", follow_up[1]["content"])
        self.assertEqual(follow_up[2], {"role": "user", "content": "Now split that by region"})
        self.assertEqual(session.cost.calls, 3)

    def test_only_the_last_three_queries_are_kept(self):
        session = analyst.Session(test_db())
        result = analyst.Result(answer=analyst.Answer(answer="Done.", value=None), queries=[f"SELECT {n}" for n in range(5)])
        session.remember("Q", result)
        self.assertTrue(session.memory[1]["content"].endswith("<sql>\nSELECT 2\nSELECT 3\nSELECT 4\n</sql>"))

    def test_memory_keeps_the_last_max_turns(self):
        session = analyst.Session(test_db())
        for n in range(analyst.MAX_TURNS + 3):
            session.remember(f"Question {n}", analyst.Result(answer=analyst.Answer(answer=f"Answer {n}", value=None)))
        self.assertEqual(len(session.memory), 2 * analyst.MAX_TURNS)
        self.assertEqual(session.memory[0], {"role": "user", "content": "Question 3"})
        self.assertEqual(session.memory[-2], {"role": "user", "content": f"Question {analyst.MAX_TURNS + 2}"})
        self.assertIn("(no queries)", session.memory[-1]["content"])


if __name__ == "__main__":
    unittest.main()
