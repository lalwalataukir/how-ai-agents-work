"""Milestone 5: traces and evals"""
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

sys.path[:0] = [str(Path(__file__).parent.parent), str(Path(__file__).parent)]
import fakes  # noqa: E402  (fakes sets the test environment first)
from fakes import BAD, GOOD, FakeClaude  # noqa: E402

import evals  # noqa: E402
import team  # noqa: E402
import wiki  # noqa: E402

HINT = ("cited_share: body paragraphs that aren't headings, and the share with an [n]. mentions: for each term, any of its "
        "|-separated words in the lower-cased report. run_topic: team.run, then the three grades, a score on the trace, and "
        "a row with topic, passed, cited, mentions, judge, reason, cost and seconds.")
CASE = {"topic": "The Dartmouth workshop", "must_mention": ["1956", "McCarthy", "Minsky", "Turing"]}


class GradeTest(unittest.TestCase):
    def test_cited_share_counts_paragraphs_not_headings(self):
        self.assertEqual(evals.cited_share(GOOD), 1.0)
        self.assertAlmostEqual(evals.cited_share(BAD), 2 / 3)
        self.assertEqual(evals.cited_share("# Only a title"), 0.0)

    def test_sources_are_not_part_of_the_body(self):
        self.assertEqual(evals.cited_share(GOOD + "\n\n## Sources\n\n1. [Page](url)"), 1.0)

    def test_mentions_any_spelling_any_case(self):
        self.assertEqual(evals.mentions(GOOD, CASE["must_mention"]), 0.75)
        self.assertEqual(evals.mentions("The SUN SHIELD keeps it cold.", ["sunshield|sun shield"]), 1.0)


class RunTopicTest(unittest.TestCase):
    def setUp(self):
        for patch in (mock.patch.object(wiki, "search_wikipedia", fakes.search_wikipedia),
                      mock.patch.object(wiki, "read_page", fakes.read_page)):
            patch.start()
            self.addCleanup(patch.stop)

    def test_a_topic_is_run_graded_and_judged(self):
        fake = FakeClaude()
        with mock.patch.object(team, "client", fake):
            row = evals.run_topic(CASE)
        self.assertEqual({k: row[k] for k in ("topic", "passed", "cited", "mentions", "judge")},
                         {"topic": CASE["topic"], "passed": True, "cited": 1.0, "mentions": 0.75, "judge": True})
        judge = fake.requests[-1]
        self.assertIs(judge["output_format"], evals.Verdict)
        self.assertEqual(judge["model"], evals.JUDGE_MODEL)
        self.assertIn("<findings>Q: What was the Dartmouth workshop?", judge["messages"][0]["content"])
        self.assertGreater(row["cost"], 0)

    def test_too_little_of_the_topic_fails(self):
        with mock.patch.object(team, "client", FakeClaude()):
            row = evals.run_topic(dict(CASE, must_mention=["Turing", "Shannon", "1956"]))
        self.assertFalse(row["passed"])

    def test_main_prints_a_line_a_topic_and_a_summary(self):
        out = io.StringIO()
        with mock.patch.object(team, "client", FakeClaude()), \
             mock.patch.object(evals, "TOPICS", [CASE, dict(CASE, must_mention=["Turing"])]), redirect_stdout(out):
            rows = evals.main()
        lines = out.getvalue().splitlines()
        self.assertEqual(len(rows), 2)
        self.assertTrue(lines[0].startswith("  [x] The Dartmouth workshop"))
        self.assertTrue(lines[1].startswith("  [ ] The Dartmouth workshop"))
        self.assertTrue(lines[2].startswith("1 of 2 passed."))


if __name__ == "__main__":
    unittest.main()
