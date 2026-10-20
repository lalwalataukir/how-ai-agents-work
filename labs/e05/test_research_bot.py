"""Offline tests for research_bot.py. Claude and Wikipedia are both faked."""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

import httpx

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
sys.path.insert(0, str(Path(__file__).parent))
import research_bot  # noqa: E402

SUMMARY = {"title": "Dartmouth workshop", "extract": "The 1956 Dartmouth workshop is considered the founding event of AI.",
           "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Dartmouth_workshop"}}}


def fake_get(url, params=None, headers=None, timeout=None, follow_redirects=False):
    assert headers["User-Agent"] and timeout
    request = httpx.Request("GET", url)
    if url.endswith("/search/page"):
        pages = [{"title": "Dartmouth workshop", "description": "1956 AI conference"}, {"title": "John McCarthy", "description": None}]
        return httpx.Response(200, json={"pages": pages}, request=request)
    if url.endswith("/Dartmouth_workshop"):
        return httpx.Response(200, json=SUMMARY, request=request)
    return httpx.Response(404, json={}, request=request)


def tool_use(id_, name, args):
    return NS(type="tool_use", id=id_, name=name, input=args)


def reply(blocks, stop, tokens=(100, 20)):
    return NS(content=blocks, stop_reason=stop, usage=NS(input_tokens=tokens[0], output_tokens=tokens[1]))


class FakeMessages:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def create(self, **kwargs):
        self.calls.append(dict(kwargs, messages=list(kwargs["messages"])))
        return self.replies.pop(0)


class ResearchBotTest(unittest.TestCase):
    def run_bot(self, replies):
        fake = FakeMessages(replies)
        out = io.StringIO()
        with mock.patch.object(research_bot, "client", NS(messages=fake)), \
             mock.patch.object(research_bot.httpx, "get", side_effect=fake_get), redirect_stdout(out):
            answer = research_bot.research("Who coined the term AI?")
        return answer, fake.calls, out.getvalue()

    def test_runs_both_tools_and_sends_results_back_together(self):
        answer, calls, out = self.run_bot([
            reply([NS(type="thinking", thinking=""), tool_use("t1", "search_wikipedia", {"query": "term artificial intelligence"}),
                   tool_use("t2", "read_page", {"title": "Dartmouth workshop"})], "tool_use", (1200, 90)),
            reply([NS(type="text", text="John McCarthy coined it in 1955 [Dartmouth workshop].")], "end_turn", (1900, 60)),
        ])
        self.assertEqual(answer, "John McCarthy coined it in 1955 [Dartmouth workshop].")
        self.assertEqual(calls[0]["tools"], research_bot.TOOLS)
        self.assertTrue(all(tool["strict"] for tool in calls[0]["tools"]))
        second = calls[1]["messages"]
        self.assertEqual([m["role"] for m in second], ["user", "assistant", "user"])
        results = second[2]["content"]
        self.assertEqual([r["tool_use_id"] for r in results], ["t1", "t2"])
        self.assertFalse(any(r["is_error"] for r in results))
        self.assertEqual(json.loads(results[0]["content"])[1], {"title": "John McCarthy", "description": ""})
        self.assertEqual(json.loads(results[1]["content"])["url"], "https://en.wikipedia.org/wiki/Dartmouth_workshop")
        self.assertIn('-> read_page({"title": "Dartmouth workshop"})', out)
        self.assertIn("[2 model calls, 3100 tokens in, 150 out, $0.00038]", out)

    def test_tool_errors_go_back_to_the_model(self):
        _, calls, _ = self.run_bot([
            reply([tool_use("t1", "read_page", {"title": "No such page"}), tool_use("t2", "delete_files", {})], "tool_use"),
            reply([NS(type="text", text="I couldn't find that page.")], "end_turn"),
        ])
        results = calls[1]["messages"][2]["content"]
        self.assertEqual([(r["is_error"], r["content"]) for r in results], [
            (True, "Wikipedia answered 404. Check the title and try again."),
            (True, "There is no tool called delete_files."),
        ])

    def test_stops_at_the_safety_limit(self):
        looping = [reply([tool_use(f"t{i}", "search_wikipedia", {"query": "AI"})], "tool_use") for i in range(research_bot.MAX_CALLS)]
        answer, calls, _ = self.run_bot(looping)
        self.assertEqual(len(calls), research_bot.MAX_CALLS)
        self.assertEqual(answer, "Stopped after 8 model calls without a final answer.")

    def test_cut_off_answer_is_flagged(self):
        answer, _, _ = self.run_bot([reply([NS(type="text", text="The term was")], "max_tokens")])
        self.assertEqual(answer, "The term was\n(Stopped early: max_tokens)")


if __name__ == "__main__":
    unittest.main()
