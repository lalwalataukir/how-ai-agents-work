"""Offline tests for agent.py, agent_graph.py and notes_server.py. Claude, Wikipedia and the notes
database are faked, so no API key or network is needed. LangGraph and MCP run for real."""
import asyncio
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
import chromadb  # noqa: E402
from anthropic.types import TextBlock, ThinkingBlock, ToolUseBlock  # noqa: E402

LABS = Path(__file__).parent.parent
for folder in ("e05", "e06", "e07"):  # in your repo these files sit side by side
    sys.path.insert(0, str(LABS / folder))
for name in ("agent", "agent_graph", "notes_server"):  # other labs have their own agent.py
    sys.modules.pop(name, None)
with mock.patch.object(chromadb, "PersistentClient", lambda path: chromadb.EphemeralClient()):
    import agent  # noqa: E402
    import agent_graph  # noqa: E402
    import notes_server  # noqa: E402
from langgraph.types import Command  # noqa: E402
from mcp import Client  # noqa: E402

HITS = [{"source": "handbook.md", "page": 1, "text": "Late books cost 20 cents a day.", "distance": 0.25}]


def use(id_, name, args):
    return ToolUseBlock(type="tool_use", id=id_, name=name, input=args)


def text(t):
    return TextBlock(type="text", text=t, citations=None)


def reply(blocks, stop="tool_use", tokens=(500, 50)):
    return NS(content=[ThinkingBlock(type="thinking", thinking="", signature="sig")] + blocks, stop_reason=stop,
              usage=NS(input_tokens=tokens[0], output_tokens=tokens[1]))


class FakeMessages:
    def __init__(self, replies, plan=("Search the notes", "Answer with citations")):
        self.replies, self.plan, self.calls, self.plans = list(replies), list(plan), [], []

    def parse(self, **kwargs):
        self.plans.append(kwargs)
        return NS(parsed_output=agent.Plan(steps=self.plan), usage=NS(input_tokens=200, output_tokens=40))

    def create(self, **kwargs):
        self.calls.append(dict(kwargs, messages=list(kwargs["messages"])))
        return self.replies.pop(0)


class AgentTestCase(unittest.TestCase):
    def setUp(self):
        self.notes = Path(tempfile.mkdtemp())
        for patch in (mock.patch.object(agent, "NOTES", self.notes), mock.patch.object(agent, "index_file"),
                      mock.patch.object(agent, "search", return_value=HITS)):
            patch.start()
            self.addCleanup(patch.stop)

    def fake(self, replies, **kwargs):
        fake = FakeMessages(replies, **kwargs)
        patch = mock.patch.object(agent, "client", NS(messages=fake))
        patch.start()
        self.addCleanup(patch.stop)
        return fake

    def run_agent(self, question="What's the late fee?", memory=(), **kwargs):
        events = list(agent.steps(question, list(memory), **kwargs))
        return events, events[-1]


class StepsTest(AgentTestCase):
    def test_plans_then_uses_tools_then_answers(self):
        fake = self.fake([reply([use("t1", "search_notes", {"query": "late fee"})]),
                          reply([text("20 cents a day [handbook.md, page 1].")], "end_turn")])
        events, done = self.run_agent()
        self.assertEqual([e["type"] for e in events], ["plan", "tool", "done"])
        self.assertEqual(events[0]["steps"], ["Search the notes", "Answer with citations"])
        self.assertEqual(done["answer"], "20 cents a day [handbook.md, page 1].")
        self.assertEqual((done["calls"], done["tokens_in"], done["tokens_out"]), (3, 1200, 140))
        self.assertAlmostEqual(done["cost"], (1200 * 0.10 + 140 * 0.50) / 1e6)
        self.assertEqual(done["tools"], ["search_notes"])
        first = fake.calls[0]["messages"][0]["content"]
        self.assertTrue(first.startswith("What's the late fee?\n\n<plan>\n1. Search the notes\n2. Answer"))
        result = fake.calls[1]["messages"][2]["content"][0]
        self.assertEqual((result["tool_use_id"], json.loads(result["content"]), result["is_error"]), ("t1", HITS, False))
        self.assertEqual(fake.plans[0]["output_format"], agent.Plan)

    def test_wikipedia_tools_reuse_the_e5_code(self):
        self.fake([reply([use("t1", "read_page", {"title": "Dartmouth workshop"})]), reply([text("Done.")], "end_turn")])
        with mock.patch.object(agent, "run_wiki_tool", return_value=('{"title": "Dartmouth workshop"}', False)) as wiki:
            self.run_agent()
        wiki.assert_called_once_with("read_page", {"title": "Dartmouth workshop"})

    def test_save_note_runs_only_after_a_yes(self):
        note = {"title": "Late fees", "text": "20 cents a day [handbook.md, page 1]."}
        fake = self.fake([reply([use("t1", "save_note", note)]), reply([text("Saved.")], "end_turn")])
        approve = mock.Mock(return_value=True)
        self.run_agent("Save that as a note", approve=approve)
        approve.assert_called_once_with("save_note", note)
        [path] = self.notes.iterdir()
        self.assertTrue(path.name.endswith("-late-fees.md"))
        self.assertEqual(path.read_text(), "# Late fees\n\n20 cents a day [handbook.md, page 1].\n")
        agent.index_file.assert_called_once_with(path, self.notes)
        self.assertEqual(json.loads(fake.calls[1]["messages"][2]["content"][0]["content"]), {"saved": path.name})

    def test_save_note_is_skipped_after_a_no(self):
        fake = self.fake([reply([use("t1", "save_note", {"title": "x", "text": "y"})]), reply([text("Not saved.")], "end_turn")])
        self.run_agent("Save that", approve=lambda name, args: False)
        self.assertEqual(list(self.notes.iterdir()), [])
        result = fake.calls[1]["messages"][2]["content"][0]
        self.assertTrue(result["is_error"])
        self.assertIn("The user said no", result["content"])

    def test_tools_outside_the_allowed_list_are_refused(self):
        fake = self.fake([reply([use("t1", "save_note", {"title": "x", "text": "y"})]), reply([text("OK.")], "end_turn")])
        approve = mock.Mock(return_value=True)
        self.run_agent(tools=["search_wikipedia", "read_page"], approve=approve)
        self.assertEqual([t["name"] for t in fake.calls[0]["tools"]], ["search_wikipedia", "read_page"])
        approve.assert_not_called()
        self.assertEqual(fake.calls[1]["messages"][2]["content"][0]["content"], "There is no tool called save_note.")

    def test_a_repeated_call_is_answered_from_before(self):
        again = {"query": "late fee"}
        fake = self.fake([reply([use("t1", "search_notes", again)]), reply([use("t2", "search_notes", again)]),
                          reply([text("20 cents.")], "end_turn")])
        self.run_agent()
        self.assertEqual(agent.search.call_count, 1)
        self.assertEqual(fake.calls[2]["messages"][4]["content"][0]["content"], "You already made this exact call. Use its result above.")

    def test_stops_at_the_call_limit(self):
        looping = [reply([use(f"t{i}", "search_notes", {"query": f"try {i}"})]) for i in range(20)]
        fake = self.fake(looping)
        events, done = self.run_agent()
        self.assertEqual(done["calls"], agent.MAX_CALLS)
        self.assertEqual(len(fake.calls), agent.MAX_CALLS - 1)  # the plan was the first call
        self.assertTrue(done["answer"].startswith("Stopped: this question reached its limit of 10 model calls"))

    def test_stops_at_the_cost_limit(self):
        expensive = [reply([use(f"t{i}", "search_notes", {"query": f"try {i}"})], tokens=(150_000, 100)) for i in range(5)]
        fake = self.fake(expensive)
        _, done = self.run_agent()
        self.assertEqual(len(fake.calls), 2)
        self.assertGreaterEqual(done["cost"], agent.MAX_COST)

    def test_cut_off_answers_are_flagged(self):
        self.fake([reply([text("The fee is")], "max_tokens")])
        _, done = self.run_agent()
        self.assertEqual(done["answer"], "The fee is\n(Stopped early: max_tokens)")


class AskTest(AgentTestCase):
    def test_memory_keeps_questions_and_answers_for_follow_ups(self):
        fake = self.fake([reply([text("20 cents a day [handbook.md, page 1].")], "end_turn"),
                          reply([text("Up to $5 per item.")], "end_turn")])
        memory, out = [], io.StringIO()
        with redirect_stdout(out):
            agent.ask("What's the late fee?", memory)
            agent.ask("Is there a cap?", memory)
        self.assertEqual(memory, [
            {"role": "user", "content": "What's the late fee?"},
            {"role": "assistant", "content": "20 cents a day [handbook.md, page 1]."},
            {"role": "user", "content": "Is there a cap?"},
            {"role": "assistant", "content": "Up to $5 per item."},
        ])
        self.assertEqual(fake.calls[1]["messages"][:2], memory[:2])
        self.assertEqual(fake.plans[1]["messages"][:2], memory[:2])
        self.assertIn("  plan: Search the notes | Answer with citations", out.getvalue())
        self.assertIn("  [2 model calls, 700 tokens in, 90 out, $0.00012]", out.getvalue())


class GraphTest(AgentTestCase):
    def config(self):
        return {"configurable": {"thread_id": self.id()}}

    def test_pauses_for_approval_then_resumes(self):
        note = {"title": "Late fees", "text": "20 cents a day."}
        fake = self.fake([reply([use("t1", "search_notes", {"query": "late"}), use("t2", "save_note", note)]),
                          reply([text("Saved your note.")], "end_turn")])
        with redirect_stdout(io.StringIO()):
            result = agent_graph.graph.invoke({"messages": [{"role": "user", "content": "Save the late fee as a note"}]}, self.config())
            self.assertEqual(result["__interrupt__"][0].value, {"tool": "save_note", "input": note})
            self.assertEqual(list(self.notes.iterdir()), [])  # nothing runs while it waits
            result = agent_graph.graph.invoke(Command(resume=True), self.config())
        self.assertNotIn("__interrupt__", result)
        self.assertEqual(len(list(self.notes.iterdir())), 1)
        self.assertEqual(agent.search.call_count, 1)
        self.assertEqual(result["messages"][-1]["content"][-1], {"type": "text", "text": "Saved your note.", "citations": None})
        self.assertEqual((result["calls"], round(result["cost"], 6)), (3, round((1200 * 0.10 + 140 * 0.50) / 1e6, 6)))
        roles = [m["role"] for m in result["messages"]]
        self.assertEqual(roles, ["user", "user", "assistant", "user", "assistant"])
        self.assertIsInstance(fake.calls[1]["messages"][2]["content"][0], dict)  # plain data in the state

    def test_a_no_skips_the_save_and_the_thread_remembers(self):
        fake = self.fake([reply([use("t1", "save_note", {"title": "x", "text": "y"})]),
                          reply([text("Not saved.")], "end_turn"), reply([text("You asked about late fees.")], "end_turn")])
        with redirect_stdout(io.StringIO()):
            agent_graph.graph.invoke({"messages": [{"role": "user", "content": "Save it"}]}, self.config())
            agent_graph.graph.invoke(Command(resume=False), self.config())
            result = agent_graph.graph.invoke({"messages": [{"role": "user", "content": "What did I ask?"}]}, self.config())
        self.assertEqual(list(self.notes.iterdir()), [])
        self.assertIn("The user said no", fake.calls[1]["messages"][3]["content"][0]["content"])
        self.assertEqual(len(fake.calls[2]["messages"]), 7)  # the whole thread so far, then the new question and plan
        self.assertEqual(result["calls"], 2)  # limits reset for each question

    def test_ask_prints_the_answer_and_cost(self):
        self.fake([reply([text("20 cents a day.")], "end_turn")])
        out = io.StringIO()
        with redirect_stdout(out):
            answer = agent_graph.ask("Late fee?", self.config())
        self.assertEqual(answer, "20 cents a day.")
        self.assertIn("[2 model calls, $0.00012]", out.getvalue())

    def test_the_graph_stops_at_the_call_limit(self):
        self.fake([reply([use(f"t{i}", "search_notes", {"query": f"q{i}"})]) for i in range(20)])
        with redirect_stdout(io.StringIO()):
            result = agent_graph.graph.invoke({"messages": [{"role": "user", "content": "Loop"}]}, self.config())
        self.assertEqual(result["calls"], agent.MAX_CALLS)
        self.assertTrue(result["messages"][-1]["content"][0]["text"].startswith("Stopped: this question reached its limit"))

    def test_the_drawing_shows_every_step(self):
        drawing = agent_graph.graph.get_graph().draw_mermaid()
        for node in ("plan", "model", "approve", "tools"):
            self.assertIn(node, drawing)


class NotesServerTest(unittest.TestCase):
    def test_lists_and_runs_the_search_tool(self):
        async def check():
            async with Client(notes_server.mcp) as client:
                tools = (await client.list_tools()).tools
                result = await client.call_tool("search_notes", {"query": "late fee"})
            return tools, result

        with mock.patch.object(notes_server, "search", return_value=HITS) as search:
            tools, result = asyncio.run(check())
        self.assertEqual([t.name for t in tools], ["search_notes"])
        self.assertEqual(tools[0].input_schema["required"], ["query"])
        self.assertIn("own notes", tools[0].description)
        search.assert_called_once_with("late fee")
        self.assertEqual(result.structured_content, {"result": HITS})
        self.assertFalse(result.is_error)


if __name__ == "__main__":
    unittest.main()
