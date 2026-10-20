"""Offline tests for the E8 lab: the traced agent, run_evals.py, eval_cases.json and evals.yml.
Claude is faked and Langfuse sends its traces to a tiny server inside the test, so no keys or
network are needed."""
import gzip
import http.server
import io
import json
import os
import sys
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

HERE = Path(__file__).parent
SPANS, POSTS = [], []


class FakeLangfuse(http.server.BaseHTTPRequestHandler):
    """Stands in for Langfuse Cloud: records every span it is sent."""

    def do_POST(self):
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
        body = self.rfile.read(int(self.headers["Content-Length"]))
        POSTS.append(self.path)
        if self.path.endswith("/otel/v1/traces"):
            if self.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            request = ExportTraceServiceRequest()
            request.ParseFromString(body)
            for resource in request.resource_spans:
                for scope in resource.scope_spans:
                    for span in scope.spans:
                        attrs = {a.key: [v.string_value for v in a.value.array_value.values] if a.value.HasField("array_value")
                                 else a.value.string_value or a.value.int_value for a in span.attributes}
                        SPANS.append({"name": span.name, "id": span.span_id.hex(), "parent": span.parent_span_id.hex(),
                                      "trace": span.trace_id.hex(), "scope": scope.scope.name, "attrs": attrs})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass


server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeLangfuse)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ.update(LANGFUSE_PUBLIC_KEY="pk-lf-test", LANGFUSE_SECRET_KEY="sk-lf-test", LANGFUSE_TRACING_ENABLED="true",
                  LANGFUSE_BASE_URL=f"http://127.0.0.1:{server.server_port}")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")

import anthropic  # noqa: E402
import chromadb  # noqa: E402
import httpx2  # noqa: E402
import yaml  # noqa: E402

LABS = HERE.parent
for folder in ("e05", "e06", "e08"):
    sys.path.insert(0, str(LABS / folder))
for name in ("agent", "run_evals"):  # other labs have their own agent.py
    sys.modules.pop(name, None)
with mock.patch.object(chromadb, "PersistentClient", lambda path: chromadb.EphemeralClient()):
    import agent  # noqa: E402
    import run_evals  # noqa: E402

CASES = json.loads((HERE / "eval_cases.json").read_text(encoding="utf-8"))


def message(content, stop, tokens):
    return {"id": "msg_1", "type": "message", "role": "assistant", "model": "claude-haiku-5-5", "content": content,
            "stop_reason": stop, "stop_sequence": None, "usage": {"input_tokens": tokens[0], "output_tokens": tokens[1]}}


def real_client(replies):
    """The real anthropic SDK, answering from a list instead of the network, so its traces are real too."""
    replies = list(replies)
    return anthropic.Anthropic(http_client=httpx2.Client(
        transport=httpx2.MockTransport(lambda request: httpx2.Response(200, json=replies.pop(0)))))


class CasesTest(unittest.TestCase):
    def test_twenty_well_formed_cases(self):
        self.assertEqual(len(CASES), 20)
        self.assertEqual(len({c["id"] for c in CASES}), 20)
        for case in CASES:
            self.assertEqual(set(case), {"id", "question", "expect", "must_include", "reference"}, case["id"])
            self.assertIn(case["expect"], ("answer", "no_answer"))
            self.assertEqual(case["expect"] == "answer", bool(case["must_include"]), case["id"])
        self.assertEqual(sum(c["expect"] == "no_answer" for c in CASES), 3)


class CodeChecksTest(unittest.TestCase):
    CASE = {"id": "ai-term", "expect": "answer", "must_include": ["McCarthy", "1955|1956"]}

    def test_a_good_answer_passes(self):
        answer = "John McCarthy coined it in his 1955 proposal [Dartmouth workshop]."
        self.assertEqual(run_evals.code_checks(self.CASE, answer), [])

    def test_each_problem_is_named(self):
        self.assertEqual(run_evals.code_checks(self.CASE, "Marvin Minsky did, in 1956."),
                         ["doesn't mention McCarthy", "no citation"])
        long = "McCarthy 1955 [Dartmouth workshop] " + "word " * 200
        self.assertEqual(run_evals.code_checks(self.CASE, long), ["over 200 words"])
        self.assertIn("hit a limit", run_evals.code_checks(self.CASE, "Stopped: this question reached its limit"))

    def test_no_answer_cases_need_no_citation(self):
        case = {"id": "breakfast", "expect": "no_answer", "must_include": []}
        self.assertEqual(run_evals.code_checks(case, "I can't know what you had for breakfast."), [])


class FakeJudge:
    def __init__(self, verdicts):
        self.verdicts, self.calls = list(verdicts), []

    def parse(self, **kwargs):
        self.calls.append(kwargs)
        return NS(parsed_output=self.verdicts.pop(0), usage=NS(input_tokens=600, output_tokens=40))


def fake_steps(answers):
    answers = dict(answers)

    def steps(question, memory, approve):
        assert approve("save_note", {}) is False  # evals must never save notes
        yield {"type": "plan", "steps": ["Search"]}
        yield {"type": "done", "answer": answers[question], "calls": 3, "tokens_in": 2000, "tokens_out": 100,
               "cost": 0.00025, "tools": ["search_wikipedia"]}
    return steps


class RunEvalsTest(unittest.TestCase):
    def setUp(self):
        self.report = Path(tempfile.mkdtemp()) / "eval_report.json"
        patch = mock.patch.object(run_evals, "REPORT", self.report)
        patch.start()
        self.addCleanup(patch.stop)

    def run_main(self, answers, verdicts, limit=None):
        judge = FakeJudge(verdicts)
        out = io.StringIO()
        with mock.patch.object(agent, "steps", fake_steps(answers)), \
             mock.patch.object(agent, "client", NS(messages=judge)), redirect_stdout(out):
            ok = run_evals.main(limit)
        return ok, judge, out.getvalue(), json.loads(self.report.read_text())

    def test_judge_runs_only_after_the_code_checks_pass(self):
        answers = {CASES[0]["question"]: "McCarthy, 1955 [Dartmouth workshop].", CASES[1]["question"]: "Somewhere in America."}
        ok, judge, out, report = self.run_main(answers, [run_evals.Verdict(reason="Correct and cited.", passed=True)], limit=2)
        self.assertEqual(len(judge.calls), 1)
        prompt = judge.calls[0]["messages"][0]["content"]
        self.assertIn("<reference>John McCarthy and colleagues", prompt)
        self.assertIn("<answer>McCarthy, 1955 [Dartmouth workshop].</answer>", prompt)
        self.assertIs(judge.calls[0]["output_format"], run_evals.Verdict)
        self.assertFalse(ok)
        self.assertEqual(report["score"], 0.5)
        self.assertEqual(report["results"][1]["problems"], ["doesn't mention Dartmouth", "no citation"])
        self.assertIn(" 1 pass  ai-term", out)
        self.assertIn(" 2 FAIL  dartmouth-place", out)
        self.assertIn("Score 1/2 = 50% (minimum 85%).", out)
        self.assertEqual(report["results"][0]["cost"], round(0.00025 + (600 * 0.10 + 40 * 0.50) / 1e6, 6))

    def test_a_judge_fail_is_reported_with_its_reason(self):
        answers = {CASES[0]["question"]: "McCarthy in 1956 at MIT [Dartmouth workshop]."}
        ok, _, _, report = self.run_main(answers, [run_evals.Verdict(reason="Gets the place wrong.", passed=False)], limit=1)
        self.assertFalse(ok)
        self.assertEqual(report["results"][0]["problems"], ["judge: Gets the place wrong."])

    def test_the_run_passes_at_or_above_the_minimum(self):
        good = {c["question"]: " ".join(w.split("|")[0] for w in c["must_include"]) + " [Source]" for c in CASES}
        verdicts = [run_evals.Verdict(reason="Fine.", passed=True)] * 17 + [run_evals.Verdict(reason="Wrong.", passed=False)] * 3
        ok, judge, out, report = self.run_main(good, verdicts)
        self.assertEqual(len(judge.calls), 20)
        self.assertEqual(report["score"], 0.85)
        self.assertTrue(ok)

    def test_an_api_error_fails_only_that_case(self):
        error = anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))

        def broken(question, memory, approve):
            raise error
            yield

        out = io.StringIO()
        with mock.patch.object(agent, "steps", broken), redirect_stdout(out):
            ok = run_evals.main(2)
        self.assertFalse(ok)
        self.assertIn("API error: Connection error.", out.getvalue())


class WorkflowTest(unittest.TestCase):
    def test_runs_the_evals_on_pull_requests_with_the_key_from_secrets(self):
        workflow = yaml.safe_load((HERE / "evals.yml").read_text())
        triggers = workflow[True]  # YAML reads the key "on" as True
        self.assertIn("pull_request", triggers)
        steps = workflow["jobs"]["evals"]["steps"]
        uses = [step.get("uses", "").split("@")[0] for step in steps]
        self.assertEqual(uses[:2], ["actions/checkout", "astral-sh/setup-uv"])
        run = next(step for step in steps if step.get("run") == "uv run run_evals.py")
        for key in ("ANTHROPIC_API_KEY", "LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_BASE_URL"):
            self.assertEqual(run["env"][key], "${{ secrets.%s }}" % key)
        self.assertEqual(steps[-1]["with"]["path"], run_evals.REPORT.name)
        self.assertEqual(steps[-1]["if"], "always()")


class TracingTest(unittest.TestCase):
    def test_a_run_is_one_trace_with_model_and_tool_calls_inside(self):
        SPANS.clear()
        replies = [
            message([{"type": "text", "text": json.dumps({"steps": ["Search the notes", "Answer"]})}], "end_turn", (200, 40)),
            message([{"type": "thinking", "thinking": "", "signature": "sig"},
                     {"type": "tool_use", "id": "toolu_1", "name": "search_notes", "input": {"query": "late fee"}}], "tool_use", (900, 60)),
            message([{"type": "text", "text": "20 cents a day [handbook.md, page 1]."}], "end_turn", (1200, 30)),
            message([{"type": "text", "text": json.dumps({"reason": "Correct and cited.", "passed": True})}], "end_turn", (600, 40)),
        ]
        case = {"id": "late-fee", "question": "What's the late fee?", "expect": "answer", "must_include": ["20 cents"],
                "reference": "20 cents a day, up to $5 per item."}
        with mock.patch.object(agent, "client", real_client(replies)), \
             mock.patch.object(agent, "search", return_value=[{"source": "handbook.md", "page": 1, "text": "20 cents a day.", "distance": 0.25}]):
            result = run_evals.run_case(case)
        agent.langfuse.flush()
        self.assertTrue(result["passed"])
        by_name = {}
        for span in SPANS:
            by_name.setdefault(span["name"], []).append(span)
        [root], [run], [tool] = by_name["eval-case"], by_name["agent"], by_name["run_tool"]
        models = by_name["anthropic.messages.create"]
        self.assertEqual(len(models), 4)
        self.assertEqual(root["parent"], "")
        self.assertEqual(run["parent"], root["id"])
        self.assertEqual({m["parent"] for m in models[:3]} | {tool["parent"]}, {run["id"]})
        self.assertEqual(models[3]["parent"], root["id"])  # the judge's call sits beside the agent run
        self.assertEqual(len({span["trace"] for span in SPANS}), 1)
        self.assertEqual(run["attrs"]["langfuse.observation.type"], "agent")
        self.assertIn("eval", root["attrs"]["langfuse.trace.tags"])
        self.assertEqual(tool["attrs"]["langfuse.observation.type"], "tool")
        self.assertEqual(models[1]["attrs"]["gen_ai.usage.input_tokens"], 900)
        self.assertEqual(models[1]["attrs"]["gen_ai.request.model"], "claude-haiku-5-5")


if __name__ == "__main__":
    unittest.main()
