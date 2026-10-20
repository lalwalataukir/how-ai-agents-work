"""Offline tests for check_portfolio.py. Each test builds a small project folder; the live-URL
check is faked, so no network is needed."""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import httpx

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import check_portfolio  # noqa: E402

LABS = HERE.parent
SPEC_DONE = "# Spec: Research assistant\n\n**One line:** Answers research questions with citations.\n"


def project(folder):
    """A finished project, built from the track's own lab files."""
    (folder / ".github" / "workflows").mkdir(parents=True)
    shutil.copy(LABS / "e08" / "evals.yml", folder / ".github" / "workflows" / "evals.yml")
    shutil.copy(LABS / "e08" / "eval_cases.json", folder / "eval_cases.json")
    shutil.copy(LABS / "e10" / "test_attacks.py", folder / "test_attacks.py")
    shutil.copy(LABS / "e11" / "MODEL_CHOICE.md", folder / "MODEL_CHOICE.md")
    shutil.copy(HERE / "README_TEMPLATE.md", folder / "README.md")
    (folder / "SPEC.md").write_text(SPEC_DONE, encoding="utf-8")
    (folder / ".gitignore").write_text(".venv/\n__pycache__/\n.env\nchroma/\n", encoding="utf-8")
    (folder / ".env").write_text("ANTHROPIC_API_KEY=sk-ant-api03-realkey123456\n", encoding="utf-8")
    (folder / "pyproject.toml").write_text('[project]\nname = "research-assistant"\n', encoding="utf-8")
    (folder / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    return folder


class PortfolioTest(unittest.TestCase):
    def setUp(self):
        self.root = project(Path(tempfile.mkdtemp()))

    def found(self, **kwargs):
        return [found for passed, found in check_portfolio.checks(self.root, **kwargs) if not passed]

    def test_a_finished_project_passes_every_check(self):
        self.assertEqual(self.found(), [])
        out = io.StringIO()
        with mock.patch.object(check_portfolio.Path, "cwd", return_value=self.root), redirect_stdout(out):
            ready = check_portfolio.main([])
        self.assertTrue(ready)
        self.assertIn("  [x] README links the live app: https://research-assistant-xxxx.onrender.com", out.getvalue())
        self.assertIn("  [x] 20 eval cases, run on every pull request", out.getvalue())
        self.assertTrue(out.getvalue().endswith("10 of 10 ready.\n"))

    def test_the_spec_template_as_it_comes_is_not_filled_in(self):
        shutil.copy(HERE / "SPEC.md", self.root / "SPEC.md")
        [problem] = self.found()
        self.assertRegex(problem, r"^SPEC.md still has \d+ <placeholders> to fill in$")

    def test_missing_pieces_are_named(self):
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        readme = readme.replace("## Security", "## Safety").replace("**Try it:**", "Try it:").replace("Demo video", "Demo")
        (self.root / "README.md").write_text(readme, encoding="utf-8")
        (self.root / ".gitignore").write_text(".venv/\n", encoding="utf-8")
        (self.root / "uv.lock").unlink()
        (self.root / "MODEL_CHOICE.md").unlink()
        (self.root / ".github" / "workflows" / "evals.yml").unlink()
        self.assertEqual(self.found(), [
            "README.md is missing: ## Security",
            'README has no "**Try it:** https://..." line',
            "README has no demo video link",
            ".env is not in .gitignore",
            "API keys in: .env",  # not ignored, so it would be published
            "pyproject.toml or uv.lock is missing",
            "20 eval cases, but no workflow runs run_evals.py",
            "MODEL_CHOICE.md is missing",
        ])

    def test_a_key_in_a_published_file_is_caught_but_dot_env_is_not_published(self):
        (self.root / "app_config.py").write_text('KEY = "sk-ant-api03-abcdefghijklmnop"\n', encoding="utf-8")
        self.assertEqual(self.found(), ["API keys in: app_config.py"])

    def test_in_a_git_repo_only_tracked_files_count(self):
        if shutil.which("git") is None:
            self.skipTest("git is not installed")
        run = lambda *args: subprocess.run(["git", *args], cwd=self.root, capture_output=True, check=True)
        run("init", "-q")
        (self.root / "scratch.txt").write_text("sk-ant-api03-notcommitted123", encoding="utf-8")
        run("add", "README.md")
        self.assertEqual(self.found(), [])  # scratch.txt has a key, but git doesn't track it
        run("add", "scratch.txt")
        self.assertEqual(self.found(), ["API keys in: scratch.txt"])

    def test_online_checks_the_live_app(self):
        request = httpx.Request("GET", "https://research-assistant-xxxx.onrender.com")
        with mock.patch.object(check_portfolio.httpx, "get", return_value=httpx.Response(200, request=request)) as get:
            self.assertEqual(self.found(online=True), [])
        get.assert_called_once_with("https://research-assistant-xxxx.onrender.com", timeout=90, follow_redirects=True)
        with mock.patch.object(check_portfolio.httpx, "get", side_effect=httpx.ConnectTimeout("slow")):
            self.assertEqual(self.found(online=True), ["the live app answered ConnectTimeout"])

    def test_the_exit_code_is_1_until_everything_is_ready(self):
        (self.root / "test_attacks.py").unlink()
        with mock.patch.object(check_portfolio.Path, "cwd", return_value=self.root), redirect_stdout(io.StringIO()):
            self.assertFalse(check_portfolio.main([]))


if __name__ == "__main__":
    unittest.main()
