"""Offline tests for the E9 lab: the streaming, caching agent and the FastAPI app.
Claude and Wikipedia are faked, so no API key or network is needed."""
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("LANGFUSE_TRACING_ENABLED", "false")  # no traces from these tests
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-lf-test")
import chromadb  # noqa: E402
from anthropic.types import TextBlock, ToolUseBlock  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

LABS = Path(__file__).parent.parent
for folder in ("e05", "e06", "e09"):
    sys.path.insert(0, str(LABS / folder))
for name in ("agent", "app"):  # other labs have their own agent.py
    sys.modules.pop(name, None)
with mock.patch.object(chromadb, "PersistentClient", lambda path: chromadb.EphemeralClient()):
    import agent  # noqa: E402
    import app  # noqa: E402


def usage(tokens_in, tokens_out, written=0, read=0):
    return NS(input_tokens=tokens_in, output_tokens=tokens_out, cache_creation_input_tokens=written, cache_read_input_tokens=read)


class FakeStream:
    """Plays back one reply the way client.messages.stream does: text first, then the whole message."""

    def __init__(self, blocks, stop, tokens):
        self.pieces = [piece for block in blocks if block.type == "text" for piece in block.text.split("|")]
        blocks = [text(block.text.replace("|", "")) if block.type == "text" else block for block in blocks]
        self.message = NS(content=blocks, stop_reason=stop, usage=usage(*tokens))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        return iter(self.pieces)

    def get_final_message(self):
        return self.message


class FakeMessages:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def parse(self, **kwargs):
        return NS(parsed_output=agent.Plan(steps=["Search Wikipedia", "Answer"]), usage=usage(150, 30))

    def stream(self, **kwargs):
        self.calls.append(dict(kwargs, messages=list(kwargs["messages"])))
        return FakeStream(*self.replies.pop(0))


def use(id_, name, args):
    return ToolUseBlock(type="tool_use", id=id_, name=name, input=args)


def text(t):
    return TextBlock(type="text", text=t, citations=None)


ANSWER = [([use("t1", "read_page", {"title": "Dartmouth workshop"})], "tool_use", (700, 60, 1000, 0)),
          ([text("John McCarthy| coined it| [Dartmouth workshop].")], "end_turn", (300, 40, 0, 1500))]


class AppTestCase(unittest.TestCase):
    def setUp(self):
        app.recent.clear()
        app.spent.update(day="", dollars=0.0)
        self.web = TestClient(app.app)

    def fake(self, replies):
        fake = FakeMessages(replies)
        for patch in (mock.patch.object(agent, "client", NS(messages=fake)),
                      mock.patch.object(agent, "run_wiki_tool", return_value=('{"title": "Dartmouth workshop"}', False))):
            patch.start()
            self.addCleanup(patch.stop)
        return fake

    def ask(self, question="Who coined the term AI?", client=None):
        response = (client or self.web).post("/ask", json={"question": question})
        events = [json.loads(line[6:]) for line in response.text.split("\n") if line.startswith("data: ")]
        return response, events


class StreamingAgentTest(AppTestCase):
    def test_text_arrives_in_pieces_and_cache_tokens_are_priced(self):
        fake = self.fake(ANSWER)
        events = list(agent.steps("Who coined the term AI?", [], tools=app.WEB_TOOLS))
        self.assertEqual([e["text"] for e in events if e["type"] == "text"], ["John McCarthy", " coined it", " [Dartmouth workshop]."])
        done = events[-1]
        self.assertEqual(done["answer"], "John McCarthy coined it [Dartmouth workshop].")
        self.assertEqual((done["tokens_in"], done["cache_written"], done["cache_read"], done["tokens_out"]), (1150, 1000, 1500, 130))
        self.assertAlmostEqual(done["cost"], ((1150 + 1.25 * 1000 + 0.1 * 1500) * 0.10 + 130 * 0.50) / 1e6)
        call = fake.calls[0]
        self.assertEqual(call["cache_control"], {"type": "ephemeral"})
        self.assertEqual(call["system"], [{"type": "text", "text": agent.SYSTEM, "cache_control": {"type": "ephemeral"}}])


class AppTest(AppTestCase):
    def test_home_page_and_health_check(self):
        page = self.web.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertIn("<title>Research assistant</title>", page.text)
        self.assertIn('fetch("/ask"', page.text)
        self.assertEqual(self.web.get("/health").json(), {"ok": True})

    def test_ask_streams_every_event_then_timings(self):
        fake = self.fake(ANSWER)
        response, events = self.ask()
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertEqual([e["type"] for e in events], ["plan", "tool", "text", "text", "text", "done"])
        done = events[-1]
        self.assertEqual(done["answer"], "John McCarthy coined it [Dartmouth workshop].")
        self.assertLessEqual(done["first_text"], done["seconds"])
        self.assertEqual([t["name"] for t in fake.calls[0]["tools"]], app.WEB_TOOLS)
        self.assertAlmostEqual(app.spent["dollars"], done["cost"])

    def test_no_saving_and_no_notes_on_the_public_site(self):
        fake = self.fake([([use("t1", "save_note", {"title": "x", "text": "y"}), use("t2", "search_notes", {"query": "x"})], "tool_use", (500, 50, 0, 0)),
                          ([text("I can't do that here.")], "end_turn", (600, 20, 0, 0))])
        with mock.patch.object(agent, "save_note") as save, mock.patch.object(agent, "search") as search:
            self.ask("Save a note about my notes")
        save.assert_not_called()
        search.assert_not_called()
        results = fake.calls[1]["messages"][2]["content"]
        self.assertEqual([r["content"] for r in results], ["There is no tool called save_note.", "There is no tool called search_notes."])

    def test_questions_must_be_3_to_500_characters(self):
        self.assertEqual(self.web.post("/ask", json={"question": "hi"}).status_code, 422)
        self.assertEqual(self.web.post("/ask", json={"question": "x" * 501}).status_code, 422)
        self.assertEqual(self.web.post("/ask", json={}).status_code, 422)

    def test_rate_limit_is_per_visitor(self):
        self.fake([reply for _ in range(6) for reply in ANSWER])
        statuses = [self.ask()[0].status_code for _ in range(6)]
        self.assertEqual(statuses, [200] * 5 + [429])
        self.assertEqual(self.ask()[0].json()["detail"], "Too many questions. Wait a minute and try again.")
        other = TestClient(app.app, client=("203.0.113.9", 50000))
        self.assertEqual(self.ask(client=other)[0].status_code, 200)

    def test_old_questions_stop_counting_after_a_minute(self):
        self.fake([reply for _ in range(2) for reply in ANSWER])
        with mock.patch.object(app.time, "time", return_value=1000.0):
            app.recent["testclient"].extend([900.0] * 5)  # five questions, 100 seconds ago
            self.assertEqual(self.ask()[0].status_code, 200)
        self.assertEqual(len(app.recent["testclient"]), 1)

    def test_daily_budget_turns_requests_away_until_tomorrow(self):
        self.fake(ANSWER)
        app.spent.update(day=app.date.today().isoformat(), dollars=app.DAILY_BUDGET)
        response = self.web.post("/ask", json={"question": "Who coined the term AI?"})
        self.assertEqual((response.status_code, response.json()["detail"]), (503, "Today's budget is used up. Try again tomorrow."))
        app.spent.update(day="2000-01-01")  # a new day resets the count
        self.assertEqual(self.ask()[0].status_code, 200)


if __name__ == "__main__":
    unittest.main()
