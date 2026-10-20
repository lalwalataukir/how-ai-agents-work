"""Milestone 6: a model for each role"""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path[:0] = [str(Path(__file__).parent.parent), str(Path(__file__).parent)]
import fakes  # noqa: E402, F401  (fakes sets the test environment first)

import compare_roles  # noqa: E402
import team  # noqa: E402

HINT = ("compare: keep a copy of team.ROLES, then for each choice team.ROLES.update(roles) and evals.main(limit, quiet=True); "
        "record (passed, reports, cost per report, seconds per report), and restore team.ROLES in a finally block. Then "
        "choose ROLES from what it shows.")


class RolesTest(unittest.TestCase):
    def test_every_role_has_a_known_model(self):
        self.assertEqual(sorted(team.ROLES), ["critic", "planner", "worker", "writer"])
        self.assertTrue(set(team.ROLES.values()) <= set(team.PRICES))

    def test_workers_use_the_cheapest_model_in_the_team(self):
        cheapest = min(set(team.ROLES.values()), key=lambda model: team.PRICES[model])
        self.assertEqual(team.PRICES[team.ROLES["worker"]], team.PRICES[cheapest])


class CompareTest(unittest.TestCase):
    def fake_main(self, limit=None, quiet=False):
        self.seen.append((dict(team.ROLES), limit, quiet))
        good = team.ROLES["critic"] != compare_roles.HAIKU
        return [{"passed": good, "cost": 0.01 if not good else 0.04, "seconds": 20.0},
                {"passed": True, "cost": 0.02 if not good else 0.06, "seconds": 30.0}]

    def test_each_choice_runs_the_eval_and_roles_are_restored(self):
        self.seen, before = [], dict(team.ROLES)
        with mock.patch.object(compare_roles.evals, "main", self.fake_main):
            table = compare_roles.compare(2)
        self.assertEqual([roles for roles, _, _ in self.seen], list(compare_roles.CHOICES.values()))
        self.assertTrue(all(limit == 2 and quiet for _, limit, quiet in self.seen))
        self.assertEqual(table["all Haiku"], (1, 2, 0.015, 25.0))
        self.assertEqual(table["all Sonnet"], (2, 2, 0.05, 25.0))
        self.assertEqual(team.ROLES, before)

    def test_roles_are_restored_even_when_a_run_fails(self):
        before = dict(team.ROLES)
        with mock.patch.object(compare_roles.evals, "main", side_effect=RuntimeError("overloaded")):
            with self.assertRaises(RuntimeError):
                compare_roles.compare(1)
        self.assertEqual(team.ROLES, before)

    def test_the_table(self):
        out = io.StringIO()
        with mock.patch.object(compare_roles, "compare", return_value={"all Haiku": (1, 2, 0.015, 25.0)}), redirect_stdout(out):
            compare_roles.main(2)
        self.assertEqual(out.getvalue().splitlines()[1].split(), ["all", "Haiku", "1", "of", "2", "0.0150", "25.0"])


if __name__ == "__main__":
    unittest.main()
