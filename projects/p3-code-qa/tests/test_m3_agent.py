"""Milestone 3: the agent"""
import io
import os
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: Claude is faked
sys.path.insert(0, str(Path(__file__).parent.parent))
import qa  # noqa: E402
from fakes import TINYSHOP, FakeClaude, fake_collection, reply, text, use  # noqa: E402

HINT = ("run_tool: one branch per tool, adding (path, start, end) to seen for every chunk or range it shows. "
        "check_citations: CITATION.findall(answer) gives (path, start, end); check the file exists, its length, and "
        "that some seen range covers the lines. steps: E7's loop, yielding a \"tool\" event per call and a \"done\" event last.")


def index():
    with mock.patch.object(qa, "collection", fake_collection):
        return qa.Index(TINYSHOP)


INDEX = index()


class RunToolTest(unittest.TestCase):
    def test_search_shows_chunks_with_their_lines(self):
        seen = []
        result, failed = qa.run_tool("search_code", {"query": "hash password"}, INDEX, seen)
        self.assertFalse(failed)
        self.assertIn("tinyshop/auth.py:13-17 hash_password", result)
        self.assertIn('def hash_password(password):', result)
        self.assertIn(("tinyshop/auth.py", 13, 17), seen)
        self.assertEqual(len(seen), qa.TOP_K)

    def test_read_lines_numbers_them_and_records_the_range(self):
        seen = []
        result, failed = qa.run_tool("read_lines", {"path": "tinyshop/tax.py", "start": 7, "end": 8}, INDEX, seen)
        self.assertFalse(failed)
        self.assertIn("   7 | def tax_for(region, taxable_cents):", result)
        self.assertEqual(seen, [("tinyshop/tax.py", 7, 8)])

    def test_list_dir_shows_folders_with_a_slash(self):
        result, _ = qa.run_tool("list_dir", {"path": "tinyshop"}, INDEX, [])
        self.assertIn("utils/", result)
        self.assertIn("auth.py", result)

    def test_mistakes_come_back_as_errors(self):
        result, failed = qa.run_tool("read_lines", {"path": "tinyshop/nope.py", "start": 1, "end": 5}, INDEX, [])
        self.assertTrue(failed)
        self.assertEqual(qa.run_tool("delete_file", {}, INDEX, []), ("There is no tool called delete_file.", True))


class CitationTest(unittest.TestCase):
    SEEN = [("tinyshop/auth.py", 27, 39), ("tinyshop/config.py", 1, 14)]

    def test_citations_inside_what_it_read_pass(self):
        citations, warnings = qa.check_citations("It locks [tinyshop/auth.py:31-35] after 5 tries [tinyshop/config.py:7].", self.SEEN, TINYSHOP)
        self.assertEqual(citations, [{"path": "tinyshop/auth.py", "start": 31, "end": 35}, {"path": "tinyshop/config.py", "start": 7, "end": 7}])
        self.assertEqual(warnings, [])

    def test_bad_citations_are_flagged(self):
        _, warnings = qa.check_citations("[tinyshop/admin.py:1-5] [tinyshop/tax.py:1-99] [tinyshop/auth.py:13-17]", self.SEEN, TINYSHOP)
        self.assertEqual(warnings, ["cites tinyshop/admin.py, which doesn't exist",
                                    "cites tinyshop/tax.py:1-99, past the end of the file",
                                    "cites tinyshop/auth.py:13-17, which it didn't read"])


class StepsTest(unittest.TestCase):
    def run_steps(self, *replies, question="How does login lock an account?"):
        fake = FakeClaude(*replies)
        with mock.patch.object(qa, "client", fake):
            events = list(qa.steps(question, INDEX))
        return events, fake.requests

    def test_search_read_answer(self):
        events, requests = self.run_steps(
            reply(use(1, "search_code", {"query": "login lock"})),
            reply(use(2, "read_lines", {"path": "tinyshop/auth.py", "start": 27, "end": 39})),
            reply(text("After 5 wrong passwords the account locks for 15 minutes [tinyshop/auth.py:31-35].")))
        self.assertEqual([e["type"] for e in events], ["tool", "tool", "done"])
        done = events[-1]
        self.assertEqual(done["citations"], [{"path": "tinyshop/auth.py", "start": 31, "end": 35}])
        self.assertEqual((done["warnings"], done["calls"]), ([], 3))
        self.assertAlmostEqual(done["cost"], 3 * (1500 * 0.10 + 120 * 0.50) / 1_000_000)
        first = requests[0]
        self.assertEqual((first["system"], first["tools"]), (qa.SYSTEM, qa.TOOLS))
        sent = requests[2]["messages"][-1]["content"][0]
        self.assertEqual((sent["tool_use_id"], sent["is_error"]), ("toolu_2", False))
        self.assertIn("31 |", sent["content"])

    def test_an_unread_citation_is_flagged(self):
        events, _ = self.run_steps(reply(text("It's in [tinyshop/auth.py:27-39].")))
        self.assertEqual(events[-1]["warnings"], ["cites tinyshop/auth.py:27-39, which it didn't read"])

    def test_it_stops_at_max_calls(self):
        events, requests = self.run_steps(*[reply(use(n, "list_dir", {"path": "."})) for n in range(qa.MAX_CALLS)])
        self.assertEqual(len(requests), qa.MAX_CALLS)
        self.assertIn("Stopped after", events[-1]["answer"])

    def test_ask_prints_the_answer(self):
        out = io.StringIO()
        with mock.patch.object(qa, "client", FakeClaude(reply(text("Done.")))), redirect_stdout(out), redirect_stderr(io.StringIO()):
            qa.ask("Anything?", INDEX)
        self.assertEqual(out.getvalue().splitlines(), ["Done.", "[1 model calls, $0.0002]"])


if __name__ == "__main__":
    unittest.main()
