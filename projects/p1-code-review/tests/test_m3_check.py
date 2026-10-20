"""Milestone 3: check every finding"""
import io
import os
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: Claude is faked
sys.path.insert(0, str(Path(__file__).parent.parent))
import reviewer  # noqa: E402
from fakes import FakeClaude, answer  # noqa: E402

HINT = ("In check, build {path: change.added} from the changes, then add a problem for each finding whose "
        "file isn't a key, or whose line isn't in that file's added lines. In review, loop up to attempts "
        "times: ask, check, and if there are problems, add them as a user message and ask again.")
SAMPLE = Path(__file__).parent.parent / "sample"
CHANGES = reviewer.parse_diff((SAMPLE / "changes.diff").read_text(encoding="utf-8"))


def finding(file, line, severity="high"):
    return reviewer.Finding(file=file, line=line, severity=severity, issue="A problem.", fix="A fix.")


def review_of(*findings):
    return reviewer.Review(findings=list(findings), summary="A change.")


CONTEXT_LINE = next(n for mark, n, _ in CHANGES[3].rows if mark == " ")  # a db.py line the change didn't add


class CheckTest(unittest.TestCase):
    def test_findings_on_added_lines_pass(self):
        self.assertEqual(reviewer.check(review_of(finding("shop/db.py", 25), finding("shop/cart.py", 17)), CHANGES), [])

    def test_a_line_that_was_not_added_is_a_problem(self):
        problems = reviewer.check(review_of(finding("shop/db.py", CONTEXT_LINE)), CHANGES)
        self.assertEqual(len(problems), 1)
        self.assertIn(f"shop/db.py line {CONTEXT_LINE}", problems[0])

    def test_a_file_that_is_not_in_the_diff_is_a_problem(self):
        problems = reviewer.check(review_of(finding("shop/payments.py", 7), finding("db.py", 25)), CHANGES)
        self.assertEqual(len(problems), 2)
        self.assertIn("shop/payments.py", problems[0])

    def test_no_findings_no_problems(self):
        self.assertEqual(reviewer.check(review_of(), CHANGES), [])


class ReviewTest(unittest.TestCase):
    def run_review(self, *replies):
        fake = FakeClaude(*replies)
        with mock.patch.object(reviewer, "client", fake), redirect_stderr(io.StringIO()):
            result, cost = reviewer.review(CHANGES, SAMPLE)
        return result, cost, fake.requests

    def test_a_good_review_needs_one_call(self):
        good = review_of(finding("shop/db.py", 25))
        result, cost, requests = self.run_review(answer(good))
        self.assertEqual((result, cost.calls, len(requests)), (good, 1, 1))
        self.assertIn('<file path="shop/db.py">', requests[0]["messages"][0]["content"])

    def test_a_wrong_line_is_sent_back_and_the_second_answer_used(self):
        bad, good = review_of(finding("shop/db.py", CONTEXT_LINE)), review_of(finding("shop/db.py", 25))
        result, cost, requests = self.run_review(answer(bad), answer(good))
        self.assertEqual((result, cost.calls), (good, 2))
        retry = requests[1]["messages"][-1]
        self.assertEqual(retry["role"], "user")
        self.assertIn(f"shop/db.py line {CONTEXT_LINE}", retry["content"])

    def test_still_wrong_after_two_attempts_keeps_only_the_right_findings(self):
        mixed = review_of(finding("shop/db.py", 25), finding("shop/db.py", CONTEXT_LINE), finding("shop/payments.py", 7))
        result, cost, _ = self.run_review(answer(mixed), answer(mixed))
        self.assertEqual([(f.file, f.line) for f in result.findings], [("shop/db.py", 25)])
        self.assertEqual(cost.calls, 2)

    def test_stopping_early_is_an_error_not_a_review(self):
        cut = answer(review_of())
        cut.stop_reason = "max_tokens"
        with self.assertRaises(RuntimeError):
            self.run_review(cut)


if __name__ == "__main__":
    unittest.main()
