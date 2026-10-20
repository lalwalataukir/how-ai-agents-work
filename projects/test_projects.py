"""Checks on the guided projects themselves. Learners never see these: they run with the lab tests.

- every starter zip matches the finished code it is built from;
- after N milestones, the checker says exactly milestones 1 to N are done;
- the requests each project sends get through the real Anthropic SDK, with only the network faked.
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import anthropic
import httpx2

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402

LINE = re.compile(r"^  \[(x| |!)\] (\d+) ", re.MULTILINE)


class StarterTest(unittest.TestCase):
    def test_the_zips_are_up_to_date(self):
        for folder in build.PROJECTS:
            self.assertEqual(build.zip_path(folder).read_bytes(), build.starter_zip(folder),
                             f"run python projects/build.py to rebuild {folder}")

    def test_every_project_has_the_same_checker(self):
        for folder in build.PROJECTS:
            self.assertEqual((HERE / folder / "check.py").read_bytes(), (HERE / "check.py").read_bytes(), folder)

    def test_the_zip_holds_the_starter_and_no_private_files(self):
        for folder, (name, _) in build.PROJECTS.items():
            names = zipfile.ZipFile(build.zip_path(folder)).namelist()
            self.assertIn(f"{name}/check.py", names)
            self.assertIn(f"{name}/uv.lock", names)
            self.assertFalse([n for n in names if "__pycache__" in n or n.endswith("/.env") or ".venv" in n], names)
            code = "".join(zipfile.ZipFile(build.zip_path(folder)).read(n).decode() for n in names if n.endswith(".py"))
            self.assertNotIn("# BEGIN m", code)
            self.assertNotIn("#>", code)

    def test_after_n_milestones_exactly_n_are_done(self):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        for folder, (_, count) in build.PROJECTS.items():
            for stage in range(count + 1):
                with self.subTest(folder=folder, stage=stage), tempfile.TemporaryDirectory() as tmp:
                    build.snapshot(folder, stage, tmp)
                    run = subprocess.run([sys.executable, "check.py"], cwd=tmp, capture_output=True, text=True, env=env)
                    marks = {int(n): mark for mark, n in LINE.findall(run.stdout)}
                    self.assertEqual(sorted(marks), list(range(1, count + 1)), run.stdout + run.stderr)
                    self.assertEqual([n for n, mark in marks.items() if mark == "x"], list(range(1, stage + 1)), run.stdout)
                    if stage < count:
                        self.assertEqual(marks[stage + 1], " ", run.stdout)  # the next one reads "not started"
                        self.assertIn(f"Next: milestone {stage + 1}.", run.stdout)
                    self.assertEqual(run.returncode, 0 if stage == count else 1, run.stdout)


class FakeAPI:
    """Answers like the Messages API, in order, and keeps the JSON body of every request."""

    def __init__(self, *contents, respond=None):
        self.contents, self.bodies, self.respond = list(contents), [], respond  # respond(body) -> content, for any order

    def __call__(self, request):
        body = json.loads(request.content)
        self.bodies.append(body)
        content = self.respond(body) if self.respond else self.contents.pop(0)
        stop = "tool_use" if any(block["type"] == "tool_use" for block in content) else "end_turn"
        return httpx2.Response(200, json={
            "id": f"msg_{len(self.bodies)}", "type": "message", "role": "assistant", "model": body["model"],
            "content": content, "stop_reason": stop, "stop_sequence": None,
            "usage": {"input_tokens": 1000, "output_tokens": 100}})

    def client(self):
        return anthropic.Anthropic(api_key="test-key", max_retries=0,
                                   http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(self)))


def load(folder, name):
    """Import a project's module fresh, so projects with the same file names don't mix."""
    sys.modules.pop(name, None)
    sys.path.insert(0, str(HERE / folder))
    try:
        return __import__(name)
    finally:
        sys.path.remove(str(HERE / folder))


class CodeReviewerSDKTest(unittest.TestCase):
    def test_a_review_with_a_file_read_goes_through_the_real_sdk(self):
        reviewer = load("p1-code-review", "reviewer")
        sample = HERE / "p1-code-review" / "sample"
        answer = {"summary": "Adds an email search.", "findings": [
            {"file": "shop/db.py", "line": 25, "severity": "high", "issue": "SQL injection.", "fix": "Use ?."}]}
        api = FakeAPI([{"type": "tool_use", "id": "toolu_1", "name": "read_file",
                        "input": {"path": "shop/payments.py", "start": 7, "end": 9}}],
                      [{"type": "text", "text": json.dumps(answer)}])
        changes = reviewer.parse_diff((sample / "changes.diff").read_text(encoding="utf-8"))
        with mock.patch.object(reviewer, "client", api.client()), redirect_stderr(io.StringIO()):
            result, cost = reviewer.review(changes, sample)
        first, second = api.bodies
        self.assertEqual(first["output_config"]["format"]["type"], "json_schema")
        schema = first["output_config"]["format"]["schema"]
        self.assertEqual(set(schema["properties"]), {"findings", "summary"})
        self.assertIn("high", json.dumps(schema))
        self.assertEqual((first["tools"][0]["name"], first["tools"][0]["strict"]), ("read_file", True))
        self.assertEqual(first["model"], "claude-haiku-5-5")
        sent = second["messages"][-1]["content"][0]
        self.assertEqual((sent["type"], sent["tool_use_id"], sent["is_error"]), ("tool_result", "toolu_1", False))
        self.assertIn("def refund", sent["content"])
        self.assertIsInstance(result.findings[0], reviewer.Finding)
        self.assertEqual((result.findings[0].line, cost.calls), (25, 2))

    def test_score_counts_planted_bugs_by_file_and_line_range(self):
        reviewer = load("p1-code-review", "reviewer")
        score = load("p1-code-review", "score")
        planted = json.loads((HERE / "p1-code-review" / "sample" / "planted.json").read_text(encoding="utf-8"))
        f = lambda file, line: reviewer.Finding(file=file, line=line, severity="high", issue="x", fix="y")
        found, extra = score.match([f("shop/db.py", 25), f("shop/cart.py", 17), f("shop/cart.py", 30)], planted)
        self.assertEqual([bug["file"] for bug in found], ["shop/cart.py", "shop/db.py"])
        self.assertEqual([(e.file, e.line) for e in extra], [("shop/cart.py", 30)])


class DataAgentSDKTest(unittest.TestCase):
    def test_a_question_with_a_query_and_a_chart_goes_through_the_real_sdk(self):
        analyst = load("p2-data-agent", "analyst")
        make_data = load("p2-data-agent", "make_data")
        tmp = Path(tempfile.mkdtemp())
        make_data.build(tmp / "shop.db")
        count = "SELECT COUNT(*) FROM orders WHERE status = 'completed'"
        monthly = "SELECT substr(ordered_at, 1, 7), COUNT(*) FROM orders GROUP BY 1"
        api = FakeAPI([{"type": "tool_use", "id": "toolu_1", "name": "run_sql", "input": {"sql": count}},
                       {"type": "tool_use", "id": "toolu_2", "name": "make_chart",
                        "input": {"title": "Orders by month", "kind": "line", "sql": monthly}}],
                      [{"type": "text", "text": json.dumps({"answer": "1,755 completed orders.", "value": 1755})}])
        with mock.patch.object(analyst, "client", api.client()), mock.patch.object(analyst, "HERE", tmp), \
             mock.patch.object(analyst, "CHARTS", tmp / "charts"), redirect_stderr(io.StringIO()):
            result = analyst.ask("How many completed orders?", [], tmp / "shop.db", analyst.Cost())
        first, second = api.bodies
        schema = first["output_config"]["format"]["schema"]
        self.assertEqual(set(schema["properties"]), {"answer", "value"})
        self.assertEqual([t["name"] for t in first["tools"]], ["run_sql", "make_chart"])
        self.assertIn("orders (2000 rows)", first["system"])
        sent = second["messages"][-1]["content"]
        self.assertEqual([(r["tool_use_id"], r["is_error"]) for r in sent], [("toolu_1", False), ("toolu_2", False)])
        self.assertEqual(json.loads(sent[0]["content"])["rows"], [[1755]])
        self.assertEqual((result.answer.value, result.charts), (1755.0, ["charts/orders-by-month.png"]))
        self.assertTrue((tmp / "charts" / "orders-by-month.png").is_file())


class CodeQaSDKTest(unittest.TestCase):
    def test_search_read_and_cite_go_through_the_real_sdk(self):
        sys.path.insert(0, str(HERE / "p3-code-qa" / "tests"))
        sys.modules.pop("fakes", None)
        try:
            qa = load("p3-code-qa", "qa")
            import fakes
        finally:
            sys.path.remove(str(HERE / "p3-code-qa" / "tests"))
            sys.modules.pop("fakes", None)
        with mock.patch.object(qa, "collection", fakes.fake_collection):
            index = qa.Index(HERE / "p3-code-qa" / "tinyshop")
        api = FakeAPI([{"type": "tool_use", "id": "toolu_1", "name": "search_code", "input": {"query": "lock account login"}}],
                      [{"type": "tool_use", "id": "toolu_2", "name": "read_lines", "input": {"path": "tinyshop/auth.py", "start": 27, "end": 39}}],
                      [{"type": "text", "text": "Five wrong passwords lock it for 15 minutes [tinyshop/auth.py:31-35]."}])
        with mock.patch.object(qa, "client", api.client()):
            events = list(qa.steps("How does login lock an account?", index))
        first, _, third = api.bodies
        self.assertEqual([t["name"] for t in first["tools"]], ["search_code", "read_lines", "list_dir"])
        self.assertTrue(all(t["strict"] for t in first["tools"]))
        sent = third["messages"][-1]["content"][0]
        self.assertTrue(sent["content"].startswith('<untrusted source="read_lines">'))
        done = events[-1]
        self.assertEqual((done["citations"], done["warnings"], done["calls"]),
                         ([{"path": "tinyshop/auth.py", "start": 31, "end": 35}], [], 3))


TRACE_SCRIPT = r'''
import gzip, http.server, json, os, sys, threading
SPANS = []

class FakeLangfuse(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        from opentelemetry.proto.collector.trace.v1.trace_service_pb2 import ExportTraceServiceRequest
        body = self.rfile.read(int(self.headers["Content-Length"]))
        if self.path.endswith("/otel/v1/traces"):
            if self.headers.get("Content-Encoding") == "gzip":
                body = gzip.decompress(body)
            request = ExportTraceServiceRequest()
            request.ParseFromString(body)
            for resource in request.resource_spans:
                for scope in resource.scope_spans:
                    for span in scope.spans:
                        SPANS.append({"name": span.name, "id": span.span_id.hex(), "parent": span.parent_span_id.hex(),
                                      "trace": span.trace_id.hex()})
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    def log_message(self, *args):
        pass

server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), FakeLangfuse)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ.update(LANGFUSE_PUBLIC_KEY="pk-lf-test", LANGFUSE_SECRET_KEY="sk-lf-test", LANGFUSE_TRACING_ENABLED="true",
                  LANGFUSE_BASE_URL=f"http://127.0.0.1:{server.server_port}", ANTHROPIC_API_KEY="test-key")
sys.path[:0] = [sys.argv[1], sys.argv[1] + "/tests"]
import fakes, team, wiki
wiki.search_wikipedia, wiki.read_page = fakes.search_wikipedia, fakes.read_page
team.client = fakes.FakeClaude(delay=0.05)
team.run("The Dartmouth workshop")
team.langfuse.flush()
print(json.dumps(SPANS))
'''


class ResearchTeamTest(unittest.TestCase):
    def test_workers_in_threads_still_nest_under_the_run_in_one_trace(self):
        run = subprocess.run([sys.executable, "-c", TRACE_SCRIPT, str(HERE / "p4-research-team")],
                             capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
        self.assertEqual(run.returncode, 0, run.stderr)
        spans = json.loads(run.stdout.strip().splitlines()[-1])
        [root] = [s for s in spans if s["name"] == "research-team"]
        names = sorted(s["name"] for s in spans if s["parent"] == root["id"])
        self.assertEqual(names, ["critic", "planner", "worker", "worker", "worker", "writer"])
        self.assertEqual({s["trace"] for s in spans}, {root["trace"]})

    def test_every_role_goes_through_the_real_sdk_with_its_own_model(self):
        sys.modules.pop("wiki", None)
        team = load("p4-research-team", "team")
        report = "# Title\n\nFact one [1].\n\nFact two [2]."

        def respond(body):
            system, messages = body.get("system", ""), body["messages"]
            if system == team.PLANNER:
                return [{"type": "text", "text": json.dumps({"questions": ["What is A?", "What is B?"]})}]
            if system == team.CRITIC:
                return [{"type": "text", "text": json.dumps({"issues": [], "approved": True})}]
            if system == team.WRITER:
                return [{"type": "text", "text": report}]
            question = messages[0]["content"]
            if len(messages) == 1:
                return [{"type": "tool_use", "id": "toolu_1", "name": "read_page", "input": {"title": question[8]}}]
            return [{"type": "text", "text": f"{question[8]} is a letter [{question[8]}]."}]

        page = lambda title: {"title": title, "summary": f"{title} is a letter.", "url": f"https://en.wikipedia.org/wiki/{title}"}
        api = FakeAPI(respond=respond)
        with mock.patch.object(team, "client", api.client()), mock.patch.object(team.wiki, "read_page", page):
            result = team.run("Letters")
        by_system = {}
        for body in api.bodies:
            by_system.setdefault(body.get("system"), []).append(body)
        planner, critic = by_system[team.PLANNER][0], by_system[team.CRITIC][0]
        self.assertEqual(planner["output_config"]["format"]["type"], "json_schema")
        self.assertEqual(set(critic["output_config"]["format"]["schema"]["properties"]), {"issues", "approved"})
        workers = by_system[team.WORKER]
        self.assertEqual(len(workers), 4)
        self.assertTrue(all(w["model"] == team.ROLES["worker"] and w["tools"][0]["strict"] for w in workers))
        self.assertEqual(by_system[team.WRITER][0]["model"], team.ROLES["writer"])
        self.assertEqual([s["title"] for s in result.sources], ["A", "B"])
        self.assertFalse(result.revised)
        self.assertTrue(result.report.endswith("1. [A](https://en.wikipedia.org/wiki/A)\n2. [B](https://en.wikipedia.org/wiki/B)\n"))


if __name__ == "__main__":
    unittest.main()
