"""Milestone 3: the writer"""
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path[:0] = [str(Path(__file__).parent.parent), str(Path(__file__).parent)]
import fakes  # noqa: E402  (fakes sets the test environment first)
from fakes import GOOD, QUESTIONS, FakeClaude  # noqa: E402

import team  # noqa: E402

HINT = ("number_sources keeps the first copy of each title, in order. write numbers them as \"[1] Title: summary\" in the "
        "prompt with the findings, adds any issues for a revision, calls ROLES[\"writer\"] with system=WRITER, and appends "
        "\"## Sources\" with \"1. [Title](url)\" lines.")


def finding(question, *titles):
    return team.Finding(question, answer=f"About {question}", sources=[fakes.read_page(t) for t in titles], calls=3)


FINDINGS = [finding(QUESTIONS[0], "Dartmouth workshop"), finding(QUESTIONS[1], "John McCarthy", "Dartmouth workshop"),
            finding(QUESTIONS[2], "History of artificial intelligence")]


class SourcesTest(unittest.TestCase):
    def test_each_page_once_in_the_order_found(self):
        titles = [s["title"] for s in team.number_sources(FINDINGS)]
        self.assertEqual(titles, ["Dartmouth workshop", "John McCarthy", "History of artificial intelligence"])

    def test_no_findings_no_sources(self):
        self.assertEqual(team.number_sources([team.Finding("Q?")]), [])


class WriteTest(unittest.TestCase):
    def write(self, issues=()):
        fake, costs = FakeClaude(), team.Costs()
        sources = team.number_sources(FINDINGS)
        with mock.patch.object(team, "client", fake):
            report = team.write("The Dartmouth workshop", FINDINGS, sources, costs, issues)
        return report, fake.requests[0], costs

    def test_the_writer_sees_the_findings_and_numbered_sources(self):
        _, request, costs = self.write()
        prompt = request["messages"][0]["content"]
        self.assertEqual((request["model"], request["system"]), (team.ROLES["writer"], team.WRITER))
        self.assertIn("[2] John McCarthy: John McCarthy coined the term", prompt)
        self.assertIn(f"Q: {QUESTIONS[1]}\nA: About {QUESTIONS[1]}", prompt)
        self.assertIn("The Dartmouth workshop", prompt)
        self.assertNotIn("problems", prompt)
        self.assertEqual(list(costs.by_role), ["writer"])

    def test_the_report_ends_with_its_sources(self):
        report, _, _ = self.write()
        self.assertTrue(report.startswith(GOOD))
        self.assertTrue(report.endswith("## Sources\n\n1. [Dartmouth workshop](https://en.wikipedia.org/wiki/Dartmouth_workshop)\n"
                                        "2. [John McCarthy](https://en.wikipedia.org/wiki/John_McCarthy)\n"
                                        "3. [History of artificial intelligence](https://en.wikipedia.org/wiki/History_of_artificial_intelligence)\n"))

    def test_a_revision_lists_the_issues(self):
        _, request, _ = self.write(issues=["[7] is cited, but there are only 3 sources."])
        self.assertIn("- [7] is cited, but there are only 3 sources.", request["messages"][0]["content"])

    def test_a_question_with_no_answer_is_marked(self):
        fake = FakeClaude()
        with mock.patch.object(team, "client", fake):
            team.write("Topic", [team.Finding("Lost question?", stopped="budget")], [], team.Costs())
        self.assertIn("Q: Lost question?\nA: (nothing found: budget)", fake.requests[0]["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
