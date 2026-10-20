"""Milestone 2: a structured review"""
import io
import os
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

from pydantic import ValidationError

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: Claude is faked
sys.path.insert(0, str(Path(__file__).parent.parent))
import reviewer  # noqa: E402
from fakes import FakeClaude, answer, reads  # noqa: E402

HINT = ("Finding needs exactly five fields: file, line, severity, issue and fix, with severity typed as "
        'Literal["high", "medium", "low"]. In ask, call client.messages.parse(..., output_format=Review), '
        "add response.usage to cost, and loop while stop_reason is \"tool_use\", as in E5.")


def a_review():
    finding = reviewer.Finding(file="shop/db.py", line=25, severity="high",
                               issue="The email is pasted into the SQL.", fix="Use a ? placeholder.")
    return reviewer.Review(findings=[finding], summary="Adds an email search.")


class SchemaTest(unittest.TestCase):
    def test_a_finding_has_five_fields(self):
        self.assertEqual(set(reviewer.Finding.model_fields), {"file", "line", "severity", "issue", "fix"})
        finding = a_review().findings[0]
        self.assertEqual((finding.file, finding.line, finding.severity), ("shop/db.py", 25, "high"))

    def test_severity_is_high_medium_or_low(self):
        with self.assertRaises(ValidationError):
            reviewer.Finding(file="a.py", line=1, severity="critical", issue="x", fix="y")

    def test_line_must_be_a_number(self):
        with self.assertRaises(ValidationError):
            reviewer.Finding(file="a.py", line="near the top", severity="low", issue="x", fix="y")

    def test_a_review_has_findings_and_a_summary(self):
        self.assertEqual(set(reviewer.Review.model_fields), {"findings", "summary"})
        self.assertEqual(reviewer.Review(findings=[], summary="Fine.").findings, [])


class AskTest(unittest.TestCase):
    def test_one_call_asks_for_a_review_and_counts_its_cost(self):
        fake, cost = FakeClaude(answer(a_review())), reviewer.Cost()
        messages = [{"role": "user", "content": "Review this change."}]
        with mock.patch.object(reviewer, "client", fake):
            response = reviewer.ask(messages, "sample", cost)
        self.assertEqual(response.parsed_output, a_review())
        [request] = fake.requests
        self.assertIs(request["output_format"], reviewer.Review)
        self.assertEqual((request["model"], request["system"], request["tools"]), (reviewer.MODEL, reviewer.SYSTEM, reviewer.TOOLS))
        self.assertEqual((cost.calls, cost.tokens_in, cost.tokens_out), (1, 2000, 400))
        self.assertAlmostEqual(cost.dollars(), 0.0004)

    def test_tool_calls_are_run_and_sent_back_before_the_answer(self):
        fake, cost = FakeClaude(reads(("shop/payments.py", 1, 20), ("shop/db.py", 1, 10)), answer(a_review())), reviewer.Cost()
        run = mock.Mock(side_effect=[("code from payments.py", False), ("no such file", True)])
        with mock.patch.object(reviewer, "client", fake), mock.patch.object(reviewer, "run_tool", run), \
             redirect_stderr(io.StringIO()):
            response = reviewer.ask([{"role": "user", "content": "Review this change."}], "sample", cost)
        self.assertEqual(response.stop_reason, "end_turn")
        self.assertEqual(run.call_args_list[0].args[:3], ("read_file", {"path": "shop/payments.py", "start": 1, "end": 20}, "sample"))
        second = fake.requests[1]["messages"]
        self.assertEqual(second[1]["role"], "assistant")
        self.assertEqual(second[2], {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "toolu_1", "content": "code from payments.py", "is_error": False},
            {"type": "tool_result", "tool_use_id": "toolu_2", "content": "no such file", "is_error": True}]})
        self.assertEqual(cost.calls, 2)


if __name__ == "__main__":
    unittest.main()
