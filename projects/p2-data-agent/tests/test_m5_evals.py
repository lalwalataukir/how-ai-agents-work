"""Milestone 5: an eval with exact answers"""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: Claude is faked
sys.path.insert(0, str(Path(__file__).parent.parent))
import analyst  # noqa: E402
import evals  # noqa: E402
from fakes import test_db  # noqa: E402

HINT = ("grade: tolerance = max(0.01, abs(expected) * 0.005), then compare abs(value - expected) with it. For "
        "\"contains\", compare in lower case. main: one analyst.Cost() shared by every analyst.ask call, so the "
        "summary shows what the whole eval cost.")
CASE = {"question": "Which category earned most?", "value": 28417.55, "contains": "Garden"}
A = lambda text, value: analyst.Answer(answer=text, value=value)


class GradeTest(unittest.TestCase):
    def test_right_answers_pass_within_the_tolerance(self):
        self.assertEqual(evals.grade(A("Garden, with $28,417.55.", 28417.55), CASE), (True, "right"))
        self.assertTrue(evals.grade(A("Garden: about $28,400.", 28400), CASE)[0])  # within 0.5%
        self.assertTrue(evals.grade(A("7.1%", 7.105), {"value": 7.1})[0])  # within 0.01

    def test_wrong_numbers_fail_and_say_why(self):
        ok, why = evals.grade(A("Garden, with $25,000.", 25000), CASE)
        self.assertFalse(ok)
        self.assertEqual(why, "value 25000.0, expected 28417.55")

    def test_the_right_number_with_the_wrong_name_fails(self):
        self.assertEqual(evals.grade(A("Toys, with $28,417.55.", 28417.55), CASE), (False, "doesn't mention Garden"))

    def test_no_number_fails(self):
        self.assertEqual(evals.grade(A("I can't tell.", None), CASE), (False, "no value"))


class EvalFileTest(unittest.TestCase):
    def test_every_expected_value_matches_its_reference_query(self):
        self.assertEqual(len(evals.CASES), 10)
        for case in evals.CASES:
            row = analyst.run_sql(test_db(), case["sql"])["rows"][0]
            self.assertAlmostEqual(row[-1], case["value"], delta=0.01, msg=case["question"])
            if "contains" in case:
                self.assertEqual(row[0], case["contains"])


class MainTest(unittest.TestCase):
    def test_every_question_is_asked_fresh_and_graded(self):
        def fake_ask(question, memory, db, cost):
            self.assertEqual(list(memory), [])
            cost.calls += 2
            case = next(c for c in evals.CASES if c["question"] == question)
            value = case["value"] if question != evals.CASES[1]["question"] else 0
            return analyst.Result(answer=A(case.get("contains", "") + " answer", value), queries=["SELECT 1"])
        out = io.StringIO()
        with mock.patch.object(analyst, "ask", fake_ask), redirect_stdout(out):
            passed, total = evals.main()
        self.assertEqual((passed, total), (9, 10))
        lines = out.getvalue().splitlines()
        self.assertEqual(len(lines), 11)
        self.assertTrue(lines[1].startswith("  [ ]  2."))
        self.assertTrue(lines[-1].startswith("9 of 10 right (90%). 20 model calls"))

    def test_a_limit_runs_the_first_few(self):
        fake = mock.Mock(return_value=analyst.Result(answer=A("x", None)))
        with mock.patch.object(analyst, "ask", fake), redirect_stdout(io.StringIO()):
            self.assertEqual(evals.main(3), (0, 3))
        self.assertEqual(fake.call_count, 3)


if __name__ == "__main__":
    unittest.main()
