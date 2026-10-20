"""Milestone 4: let it read files"""
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
import reviewer  # noqa: E402
from fakes import FakeClaude, answer, reads  # noqa: E402

HINT = ("Resolve both the repo and the requested path with Path.resolve(), then refuse the path unless "
        "target.is_relative_to(root). Number lines with f\"{n:>4} | {line}\". In run_tool, check reads "
        "against MAX_READS first, and turn a ValueError into an error result instead of a crash.")
SAMPLE = Path(__file__).parent.parent / "sample"


class ReadFileTest(unittest.TestCase):
    def test_lines_come_back_numbered(self):
        self.assertEqual(reviewer.read_file(SAMPLE, "shop/payments.py", 7, 8),
                         "   7 | def refund(payment_id, amount_cents):\n"
                         '   8 |     """Send money back to the customer\'s card. PayGate refunds whatever amount it is sent,')

    def test_a_range_past_the_end_stops_at_the_last_line(self):
        text = reviewer.read_file(SAMPLE, "shop/payments.py", 15, 99)
        self.assertEqual(text.splitlines()[-1], '  17 |     return response.json()["refund_id"]')

    def test_at_most_max_lines_come_back(self):
        repo = Path(tempfile.mkdtemp())
        (repo / "big.py").write_text("\n".join(f"x = {n}" for n in range(1, 1001)), encoding="utf-8")
        self.assertEqual(len(reviewer.read_file(repo, "big.py", 1, 1000).splitlines()), reviewer.MAX_LINES)

    def test_paths_outside_the_repo_are_refused(self):
        for path in ("../reviewer.py", "/etc/passwd", "shop/../../tests/fakes.py"):
            with self.assertRaises(ValueError, msg=path):
                reviewer.read_file(SAMPLE, path, 1, 5)

    def test_env_files_are_refused(self):
        repo = Path(tempfile.mkdtemp())
        (repo / ".env").write_text("ANTHROPIC_API_KEY=secret", encoding="utf-8")
        with self.assertRaises(ValueError):
            reviewer.read_file(repo, ".env", 1, 5)

    def test_a_missing_file_is_an_error(self):
        with self.assertRaises(ValueError):
            reviewer.read_file(SAMPLE, "shop/nothing.py", 1, 5)


class RunToolTest(unittest.TestCase):
    def test_read_file_runs(self):
        text, failed = reviewer.run_tool("read_file", {"path": "shop/payments.py", "start": 7, "end": 7}, SAMPLE, 1)
        self.assertEqual((text, failed), ("   7 | def refund(payment_id, amount_cents):", False))

    def test_errors_go_back_to_claude_marked_as_errors(self):
        text, failed = reviewer.run_tool("read_file", {"path": "../../.ssh/id_rsa", "start": 1, "end": 5}, SAMPLE, 1)
        self.assertTrue(failed)
        self.assertIn("outside the repo", text)

    def test_unknown_tools_are_errors(self):
        self.assertEqual(reviewer.run_tool("delete_file", {"path": "x"}, SAMPLE, 1), ("There is no tool called delete_file.", True))

    def test_reads_stop_at_the_limit(self):
        text, failed = reviewer.run_tool("read_file", {"path": "shop/payments.py", "start": 1, "end": 5}, SAMPLE, reviewer.MAX_READS + 1)
        self.assertTrue(failed)
        self.assertIn("limit", text)

    def test_in_the_loop_claude_gets_the_file_and_the_limit_holds(self):
        many = [("shop/payments.py", 7, 7)] * (reviewer.MAX_READS + 1)
        done = reviewer.Review(findings=[], summary="Fine.")
        fake = FakeClaude(reads(*many), answer(done))
        with mock.patch.object(reviewer, "client", fake), redirect_stderr(io.StringIO()):
            reviewer.ask([{"role": "user", "content": "Review this change."}], SAMPLE, reviewer.Cost())
        results = fake.requests[1]["messages"][-1]["content"]
        self.assertEqual([r["is_error"] for r in results], [False] * reviewer.MAX_READS + [True])
        self.assertEqual(results[0]["content"], "   7 | def refund(payment_id, amount_cents):")


if __name__ == "__main__":
    unittest.main()
