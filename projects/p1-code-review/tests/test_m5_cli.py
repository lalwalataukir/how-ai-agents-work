"""Milestone 5: use it every day"""
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: Claude is faked
sys.path.insert(0, str(Path(__file__).parent.parent))
import reviewer  # noqa: E402
from fakes import FakeClaude, answer  # noqa: E402

HINT = ("git_diff runs [\"git\", \"diff\", \"HEAD\"] or [\"git\", \"diff\", \"--staged\"] with subprocess.run(..., cwd=repo, "
        "capture_output=True, text=True). should_block compares SEVERITY[finding.severity] with SEVERITY[fail_on]. "
        "main returns 1 when should_block is true, so git or CI can stop on it.")
ROOT = Path(__file__).parent.parent


def finding(file, line, severity, issue="A problem.", fix="A fix."):
    return reviewer.Finding(file=file, line=line, severity=severity, issue=issue, fix=fix)


REVIEW = reviewer.Review(summary="Adds bulk pricing and an email search.", findings=[
    finding("shop/cart.py", 17, "medium", "Skips the | last item.", "Loop over items."),
    finding("shop/db.py", 25, "high", "SQL injection.", "Use a ? placeholder."),
])


class ReportTest(unittest.TestCase):
    def test_the_report_puts_the_worst_first(self):
        cost = reviewer.Cost(calls=2, tokens_in=10000, tokens_out=2000)
        self.assertEqual(reviewer.to_markdown(REVIEW, cost), "\n".join([
            "# Code review", "", "Adds bulk pricing and an email search.", "",
            "| Severity | Where | Issue | Fix |", "|---|---|---|---|",
            "| high | `shop/db.py:25` | SQL injection. | Use a ? placeholder. |",
            "| medium | `shop/cart.py:17` | Skips the \\| last item. | Loop over items. |",
            "", "2 finding(s) · 2 model call(s) · $0.0020", ""]))

    def test_a_clean_change_says_so(self):
        report = reviewer.to_markdown(reviewer.Review(findings=[], summary="Fine."), reviewer.Cost())
        self.assertIn("No findings.", report)

    def test_blocking_follows_fail_on(self):
        medium_only = reviewer.Review(findings=[finding("a.py", 1, "medium")], summary="")
        self.assertTrue(reviewer.should_block(REVIEW, "high"))
        self.assertFalse(reviewer.should_block(medium_only, "high"))
        self.assertTrue(reviewer.should_block(medium_only, "medium"))
        self.assertTrue(reviewer.should_block(medium_only, "low"))
        self.assertFalse(reviewer.should_block(REVIEW, "never"))


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class GitTest(unittest.TestCase):
    def test_staged_and_uncommitted_changes(self):
        repo = Path(tempfile.mkdtemp())
        git = lambda *args: subprocess.run(["git", "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
                                           cwd=repo, check=True, capture_output=True)
        git("init")
        (repo / "app.py").write_text("print('hi')\n", encoding="utf-8")
        git("add", "app.py")
        git("commit", "-m", "First")
        (repo / "app.py").write_text("print('hi')\nprint('staged')\n", encoding="utf-8")
        git("add", "app.py")
        (repo / "app.py").write_text("print('hi')\nprint('staged')\nprint('not staged')\n", encoding="utf-8")
        staged = reviewer.git_diff(repo, staged=True)
        self.assertIn("+print('staged')", staged)
        self.assertNotIn("not staged", staged)
        self.assertIn("+print('not staged')", reviewer.git_diff(repo))

    def test_outside_a_repo_is_a_clear_error(self):
        with self.assertRaises(RuntimeError):
            reviewer.git_diff(tempfile.mkdtemp())


class MainTest(unittest.TestCase):
    def setUp(self):
        self.cwd = os.getcwd()
        os.chdir(tempfile.mkdtemp())
        self.addCleanup(os.chdir, self.cwd)

    def run_main(self, *args, replies=()):
        fake, out, err = FakeClaude(*replies), io.StringIO(), io.StringIO()
        with mock.patch.object(reviewer, "client", fake), redirect_stdout(out), redirect_stderr(err):
            code = reviewer.main(list(args))
        return code, out.getvalue(), err.getvalue(), fake.requests

    def test_a_high_finding_writes_the_report_and_exits_1(self):
        diff = str(ROOT / "sample" / "changes.diff")
        code, out, err, _ = self.run_main(diff, "--repo", str(ROOT / "sample"), replies=[answer(REVIEW)])
        self.assertEqual(code, 1)
        self.assertIn("| high | `shop/db.py:25` |", Path("review.md").read_text(encoding="utf-8"))
        self.assertIn("# Code review", out)
        self.assertIn("Blocked", err)

    def test_fail_on_never_exits_0(self):
        diff = str(ROOT / "sample" / "changes.diff")
        code, _, _, _ = self.run_main(diff, "--repo", str(ROOT / "sample"), "--fail-on", "never", replies=[answer(REVIEW)])
        self.assertEqual(code, 0)

    def test_prompt_prints_without_calling_claude(self):
        code, out, _, requests = self.run_main(str(ROOT / "sample" / "changes.diff"), "--prompt")
        self.assertEqual((code, requests), (0, []))
        self.assertTrue(out.startswith("Review this change."))

    def test_no_changes_means_no_call(self):
        with mock.patch.object(reviewer, "git_diff", return_value=""):
            code, out, _, requests = self.run_main("--staged")
        self.assertEqual((code, out.strip(), requests), (0, "No changes to review.", []))


if __name__ == "__main__":
    unittest.main()
