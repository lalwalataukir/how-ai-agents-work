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

    def __init__(self, *contents):
        self.contents, self.bodies = list(contents), []

    def __call__(self, request):
        body = json.loads(request.content)
        self.bodies.append(body)
        content = self.contents.pop(0)
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


if __name__ == "__main__":
    unittest.main()
