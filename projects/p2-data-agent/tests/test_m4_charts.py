"""Milestone 4: charts"""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: Claude is faked
sys.path.insert(0, str(Path(__file__).parent.parent))
import analyst  # noqa: E402
from fakes import FakeClaude, answer, calls, test_db  # noqa: E402

HINT = ("make_chart calls run_sql, so charts get the same protection as every query. Check there are two columns "
        "and the second holds numbers, then fig, ax = plt.subplots(); ax.bar(labels, values) or ax.plot(...); "
        "fig.savefig(path); plt.close(fig). chart_tool records the query and the chart in result.")
BY_REGION = "SELECT c.region, COUNT(*) FROM orders o JOIN customers c ON c.id = o.customer_id GROUP BY c.region"
BY_MONTH = "SELECT substr(ordered_at, 1, 7), COUNT(*) FROM orders GROUP BY 1"


class ChartTest(unittest.TestCase):
    def setUp(self):
        folder = Path(tempfile.mkdtemp())
        for patch in (mock.patch.object(analyst, "CHARTS", folder / "charts"), mock.patch.object(analyst, "HERE", folder)):
            patch.start()
            self.addCleanup(patch.stop)

    def test_a_bar_chart_is_saved_as_a_png(self):
        path = analyst.make_chart(test_db(), "Orders by region", "bar", BY_REGION)
        self.assertEqual(path.name, "orders-by-region.png")
        self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_a_line_chart_over_time(self):
        path = analyst.make_chart(test_db(), "Orders per month, 2025", "line", BY_MONTH)
        self.assertEqual(path.name, "orders-per-month-2025.png")
        self.assertGreater(path.stat().st_size, 5000)

    def test_the_query_needs_labels_and_numbers(self):
        for sql in ("SELECT region FROM customers", "SELECT region, name FROM customers", "SELECT id, 1, 2 FROM orders",
                    "SELECT region, COUNT(*) FROM customers WHERE region = 'Mars' GROUP BY region"):
            with self.assertRaises(ValueError, msg=sql):
                analyst.make_chart(test_db(), "x", "bar", sql)

    def test_charts_go_through_the_safe_sql_path(self):
        with self.assertRaises(ValueError):
            analyst.make_chart(test_db(), "x", "bar", "DROP TABLE orders")

    def test_the_tool_records_the_chart_and_the_query(self):
        result = analyst.Result(answer=None)
        text, failed = analyst.chart_tool({"title": "Orders by region", "kind": "bar", "sql": BY_REGION}, test_db(), result)
        self.assertFalse(failed)
        self.assertEqual((result.charts, result.queries), (["charts/orders-by-region.png"], [BY_REGION]))
        self.assertIn("orders-by-region.png", text)

    def test_in_the_agent_a_bad_chart_is_an_error_claude_can_fix(self):
        fake = FakeClaude(calls(("make_chart", {"title": "x", "kind": "bar", "sql": "SELECT region FROM customers"})),
                          answer("Couldn't chart it.", None))
        with mock.patch.object(analyst, "client", fake), redirect_stderr(io.StringIO()):
            result = analyst.ask("Chart it", [], test_db(), analyst.Cost())
        sent = fake.requests[1]["messages"][-1]["content"][0]
        self.assertTrue(sent["is_error"])
        self.assertIn("two columns", sent["content"])
        self.assertEqual(result.charts, [])


if __name__ == "__main__":
    unittest.main()
