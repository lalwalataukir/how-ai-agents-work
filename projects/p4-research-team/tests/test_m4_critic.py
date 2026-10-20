"""Milestone 4: the critic, and the whole run"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path[:0] = [str(Path(__file__).parent.parent), str(Path(__file__).parent)]
import fakes  # noqa: E402  (fakes sets the test environment first)
from fakes import BAD, GOOD, QUESTIONS, FakeClaude  # noqa: E402

import team  # noqa: E402
import wiki  # noqa: E402

HINT = ("citation_problems: re.findall(r\"\\[(\\d+)\\]\", body) for numbers out of range, and a problem for each body paragraph "
        "(split on blank lines, skipping # headings) with no [n]. critique: those problems, plus the critic's issues unless it "
        "approved. run: plan, research_all, number_sources, write, critique, and write again with the issues if there are any.")
SOURCES = [fakes.read_page(t) for t in ("Dartmouth workshop", "John McCarthy", "History of artificial intelligence")]


class CitationTest(unittest.TestCase):
    def test_a_good_report_has_no_problems(self):
        self.assertEqual(team.citation_problems(GOOD + "\n\n## Sources\n\n1. [x](y)", 3), [])

    def test_bad_numbers_and_uncited_paragraphs(self):
        problems = team.citation_problems(BAD, 3)
        self.assertEqual(problems[0], "[7] is cited, but there are only 3 sources.")
        self.assertTrue(problems[1].startswith("This paragraph has no citation: John McCarthy organised it"))
        self.assertEqual(len(problems), 2)


class CritiqueTest(unittest.TestCase):
    def critique(self, report, critiques):
        fake, costs = FakeClaude(critiques=critiques), team.Costs()
        with mock.patch.object(team, "client", fake):
            return team.critique(report, [], SOURCES, costs), fake.requests, costs

    def test_approved_and_clean_means_no_issues(self):
        issues, requests, costs = self.critique(GOOD, [(True, ["a quibble it approved anyway"])])
        self.assertEqual(issues, [])
        self.assertIs(requests[0]["output_format"], team.Critique)
        self.assertEqual((requests[0]["model"], list(costs.by_role)), (team.ROLES["critic"], ["critic"]))

    def test_code_problems_come_first_then_the_critics(self):
        issues, _, _ = self.critique(BAD, [(False, ["The report leaves out what the workshop led to."])])
        self.assertEqual(issues[0], "[7] is cited, but there are only 3 sources.")
        self.assertEqual(issues[-1], "The report leaves out what the workshop led to.")


class RunTest(unittest.TestCase):
    def setUp(self):
        for patch in (mock.patch.object(wiki, "search_wikipedia", fakes.search_wikipedia),
                      mock.patch.object(wiki, "read_page", fakes.read_page)):
            patch.start()
            self.addCleanup(patch.stop)

    def run_team(self, fake):
        with mock.patch.object(team, "client", fake):
            return team.run("The Dartmouth workshop")

    def test_an_approved_draft_is_the_report(self):
        fake = FakeClaude()
        result = self.run_team(fake)
        self.assertEqual((result.questions, result.revised, result.issues), (QUESTIONS, False, []))
        self.assertTrue(result.report.startswith(GOOD))
        self.assertEqual(len(result.sources), 3)
        self.assertEqual(len(fake.by(team.WRITER)), 1)
        self.assertEqual(sorted(result.costs.by_role), ["critic", "planner", "worker", "writer"])
        self.assertEqual(result.costs.calls, 1 + 9 + 1 + 1)

    def test_a_draft_with_problems_is_revised_once(self):
        fake = FakeClaude(drafts=(BAD, GOOD), critiques=((False, ["Paragraph 2 has no citation."]), (True, [])))
        result = self.run_team(fake)
        self.assertTrue(result.revised)
        self.assertTrue(result.report.startswith(GOOD))
        second = fake.by(team.WRITER)[1]["messages"][0]["content"]
        self.assertIn("- [7] is cited, but there are only 3 sources.", second)
        self.assertIn("- Paragraph 2 has no citation.", second)
        self.assertEqual(len(fake.by(team.CRITIC)), 1)  # one critique: revising again would cost more than it finds


if __name__ == "__main__":
    unittest.main()
