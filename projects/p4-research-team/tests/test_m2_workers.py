"""Milestone 2: workers, in parallel"""
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path[:0] = [str(Path(__file__).parent.parent), str(Path(__file__).parent)]
import fakes  # noqa: E402  (fakes sets the test environment first)
from fakes import QUESTIONS, FakeClaude  # noqa: E402

import team  # noqa: E402
import wiki  # noqa: E402

HINT = ("research is E5's loop: check finding.calls against MAX_WORKER_CALLS and spent against MAX_WORKER_COST before "
        "each call, add costs.add(\"worker\", ...) to spent, and append read_page's result to finding.sources. research_all: "
        "pool.submit(contextvars.copy_context().run, research, question, costs) for each question, then future.result().")


class WorkerTestCase(unittest.TestCase):
    def setUp(self):
        for patch in (mock.patch.object(wiki, "search_wikipedia", fakes.search_wikipedia),
                      mock.patch.object(wiki, "read_page", fakes.read_page)):
            patch.start()
            self.addCleanup(patch.stop)

    def research(self, fake, question=QUESTIONS[1]):
        costs = team.Costs()
        with mock.patch.object(team, "client", fake):
            return team.research(question, costs), costs


class ResearchTest(WorkerTestCase):
    def test_search_read_answer_and_the_pages_are_recorded(self):
        fake = FakeClaude()
        finding, costs = self.research(fake)
        self.assertEqual((finding.question, finding.calls, finding.stopped), (QUESTIONS[1], 3, ""))
        self.assertIn("[John McCarthy]", finding.answer)
        self.assertEqual([s["title"] for s in finding.sources], ["John McCarthy"])
        self.assertEqual(set(finding.sources[0]), {"title", "summary", "url"})
        first = fake.requests[0]
        self.assertEqual((first["model"], first["system"], first["tools"]), (team.ROLES["worker"], team.WORKER, wiki.TOOLS))
        self.assertEqual(costs.calls, 3)

    def test_a_worker_stops_at_its_call_budget(self):
        finding, costs = self.research(FakeClaude(tools_forever=True))
        self.assertEqual((finding.calls, finding.stopped, finding.answer), (team.MAX_WORKER_CALLS, "budget", ""))

    def test_a_worker_stops_at_its_cost_budget(self):
        with mock.patch.object(team, "MAX_WORKER_COST", 0.0002):  # each fake call costs $0.00015
            finding, _ = self.research(FakeClaude(tools_forever=True))
        self.assertEqual((finding.calls, finding.stopped), (2, "budget"))

    def test_tool_errors_go_back_to_the_model(self):
        def broken(title):
            raise ValueError("Wikipedia answered 404. Check the title and try again.")
        fake = FakeClaude()
        with mock.patch.object(wiki, "read_page", broken):
            finding, _ = self.research(fake)
        result = fake.requests[2]["messages"][-1]["content"][0]
        self.assertTrue(result["is_error"])
        self.assertIn("404", result["content"])
        self.assertEqual(finding.sources, [])


class ParallelTest(WorkerTestCase):
    def test_workers_run_at_the_same_time_and_keep_their_order(self):
        questions = QUESTIONS + ["What is AI?"]
        fake, costs = FakeClaude(delay=0.15), team.Costs()
        start = time.perf_counter()
        with mock.patch.object(team, "client", fake):
            findings = team.research_all(questions, costs)
        seconds = time.perf_counter() - start
        self.assertEqual([f.question for f in findings], questions)
        self.assertLess(seconds, 4 * 3 * 0.15 * 0.6)  # one after another would take 1.8 s
        self.assertEqual(costs.calls, 12)

    def test_one_crashing_worker_does_not_sink_the_others(self):
        fake = FakeClaude(crash=QUESTIONS[0])
        with mock.patch.object(team, "client", fake):
            findings = team.research_all(QUESTIONS, team.Costs())
        self.assertTrue(findings[0].stopped.startswith("failed: RuntimeError"))
        self.assertTrue(findings[1].answer and findings[2].answer)

    def test_costs_add_up_correctly_from_many_threads(self):
        costs = team.Costs()
        call = mock.Mock(input_tokens=1000, output_tokens=0)
        threads = [threading.Thread(target=lambda: [costs.add("worker", call) for _ in range(500)]) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(costs.calls, 4000)


if __name__ == "__main__":
    unittest.main()
