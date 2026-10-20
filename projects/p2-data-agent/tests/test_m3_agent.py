"""Milestone 3: the agent"""
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: Claude is faked
sys.path.insert(0, str(Path(__file__).parent.parent))
import analyst  # noqa: E402
from fakes import FakeClaude, answer, calls, sql, test_db  # noqa: E402

HINT = ("Put describe_schema(db) into SYSTEM with .format(schema=...). Loop at most MAX_CALLS times: call "
        "client.messages.parse(..., tools=TOOLS, output_format=Answer), add the usage to cost, and run each "
        "tool_use block with run_tool. When stop_reason isn't \"tool_use\", put parsed_output in the Result.")
COUNT = "SELECT COUNT(*) FROM orders WHERE status = 'completed'"


def run(*replies, question="How many completed orders?", memory=()):
    fake, cost = FakeClaude(*replies), analyst.Cost()
    with mock.patch.object(analyst, "client", fake), redirect_stderr(io.StringIO()):
        result = analyst.ask(question, list(memory), test_db(), cost)
    return result, fake.requests, cost


class RunToolTest(unittest.TestCase):
    def test_a_query_runs_and_is_recorded(self):
        result = analyst.Result(answer=None)
        text, failed = analyst.run_tool("run_sql", {"sql": COUNT}, test_db(), result)
        self.assertEqual((json.loads(text)["rows"], failed), ([[1755]], False))
        self.assertEqual(result.queries, [COUNT])

    def test_a_refused_query_goes_back_as_an_error(self):
        result = analyst.Result(answer=None)
        text, failed = analyst.run_tool("run_sql", {"sql": "DROP TABLE orders"}, test_db(), result)
        self.assertTrue(failed)
        self.assertIn("Only SELECT", text)
        self.assertEqual(result.queries, ["DROP TABLE orders"])  # attempts are recorded too

    def test_unknown_tools_are_errors(self):
        self.assertEqual(analyst.run_tool("delete_rows", {}, test_db(), analyst.Result(answer=None)),
                         ("There is no tool called delete_rows.", True))


class AskTest(unittest.TestCase):
    def test_claude_queries_then_answers(self):
        result, requests, cost = run(calls(sql(COUNT)), answer("There were 1,755 completed orders.", 1755))
        self.assertEqual((result.answer.value, result.queries, cost.calls), (1755.0, [COUNT], 2))
        first = requests[0]
        self.assertIs(first["output_format"], analyst.Answer)
        self.assertEqual(first["tools"], analyst.TOOLS)
        self.assertIn("orders (2000 rows)", first["system"])
        self.assertIn("status TEXT: cancelled, completed, refunded", first["system"])
        sent = requests[1]["messages"][-1]["content"][0]
        self.assertEqual((sent["tool_use_id"], sent["is_error"], json.loads(sent["content"])["rows"]), ("toolu_1", False, [[1755]]))

    def test_a_broken_query_gets_a_second_try(self):
        fixed = "SELECT COUNT(*) FROM orders WHERE status = 'completed'"
        result, requests, _ = run(calls(sql("SELECT COUNT(*) FROM order")), calls(sql(fixed)), answer("1,755.", 1755))
        error = requests[1]["messages"][-1]["content"][0]
        self.assertTrue(error["is_error"])
        self.assertIn("SQLite", error["content"])
        self.assertEqual(result.queries, ["SELECT COUNT(*) FROM order", fixed])

    def test_memory_comes_before_the_question(self):
        memory = [{"role": "user", "content": "Earlier question"}, {"role": "assistant", "content": "Earlier answer"}]
        _, requests, _ = run(answer("Fine.", None), memory=memory)
        self.assertEqual(requests[0]["messages"][:2], memory)
        self.assertEqual(requests[0]["messages"][2], {"role": "user", "content": "How many completed orders?"})

    def test_it_stops_at_max_calls(self):
        replies = [calls(sql(f"SELECT {n}")) for n in range(analyst.MAX_CALLS)]
        result, requests, cost = run(*replies)
        self.assertEqual((len(requests), cost.calls, result.answer.value), (analyst.MAX_CALLS, analyst.MAX_CALLS, None))
        self.assertIn("Stopped", result.answer.answer)


if __name__ == "__main__":
    unittest.main()
