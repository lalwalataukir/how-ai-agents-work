"""Milestone 1: the planner"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path[:0] = [str(Path(__file__).parent.parent), str(Path(__file__).parent)]
from fakes import QUESTIONS, FakeClaude  # noqa: E402  (fakes sets the test environment first)

import team  # noqa: E402

HINT = ("client.messages.parse(model=ROLES[\"planner\"], system=PLANNER, output_format=Plan, ...), then "
        "costs.add(\"planner\", response.usage). Keep each question once (compare in lower case), raise RuntimeError "
        "when fewer than 2 are left, and return at most MAX_QUESTIONS.")


def plan_with(questions):
    fake, costs = FakeClaude(plan=questions), team.Costs()
    with mock.patch.object(team, "client", fake):
        return team.plan("The Dartmouth workshop", costs), fake.requests, costs


class PlanTest(unittest.TestCase):
    def test_the_planner_returns_its_questions(self):
        questions, requests, costs = plan_with(QUESTIONS)
        self.assertEqual(questions, QUESTIONS)
        [request] = requests
        self.assertIs(request["output_format"], team.Plan)
        self.assertEqual((request["model"], request["system"]), (team.ROLES["planner"], team.PLANNER))
        self.assertIn("The Dartmouth workshop", request["messages"][0]["content"])
        self.assertEqual((costs.calls, list(costs.by_role)), (1, ["planner"]))

    def test_repeats_and_blanks_are_dropped(self):
        questions, _, _ = plan_with(["What is it?", "  ", "what is it?", "Who made it?"])
        self.assertEqual(questions, ["What is it?", "Who made it?"])

    def test_at_most_max_questions(self):
        questions, _, _ = plan_with([f"Question {n}?" for n in range(8)])
        self.assertEqual(len(questions), team.MAX_QUESTIONS)

    def test_one_question_is_not_a_plan(self):
        with self.assertRaises(RuntimeError):
            plan_with(["Only one?"])

    def test_costs_count_by_role_and_model(self):
        costs = team.Costs()
        with mock.patch.dict(team.ROLES, {"planner": "claude-sonnet-5-5"}):
            dollars = costs.add("planner", mock.Mock(input_tokens=1_000_000, output_tokens=0))
        self.assertEqual((dollars, costs.total()), (2.0, 2.0))


if __name__ == "__main__":
    unittest.main()
