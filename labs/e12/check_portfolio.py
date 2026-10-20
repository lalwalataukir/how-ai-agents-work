"""E12 lab: check that your project is ready to show. Run it in your project folder.

Run it with:
    uv run check_portfolio.py            # checks the files
    uv run check_portfolio.py --online   # also checks that your live app answers
"""
import json
import re
import subprocess
import sys
from pathlib import Path

import httpx

SECTIONS = ["## What it does", "## How it works", "## Evals", "## Security", "## Run it yourself", "## What I'd do next"]
SECRET = re.compile(r"sk-ant-[\w-]{8,}|sk-lf-[\w-]{8,}|pk-lf-[\w-]{8,}")  # Anthropic and Langfuse keys
PLACEHOLDER = re.compile(r"<[a-z][^>\n]*>")  # the <fill this in> parts of SPEC.md
SKIP = {".venv", ".git", "chroma", "notes", "__pycache__"}


def read(root, name):
    path = root / name
    return path.read_text(encoding="utf-8") if path.is_file() else None


def published_files(root, env_ignored):
    """The files git tracks, which are what GitHub shows. If this isn't a git repo yet, every file
    that would be committed: .env only counts when .gitignore doesn't keep it out."""
    try:
        out = subprocess.run(["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True).stdout
        return [root / line for line in out.splitlines() if line]
    except (OSError, subprocess.CalledProcessError):
        return [path for path in root.rglob("*")
                if path.is_file() and not (path.name == ".env" and env_ignored)
                and not SKIP & set(path.relative_to(root).parts)]


def live_url(readme):
    match = re.search(r"\*\*Try it:\*\*\s*(https://[^\s)]+)", readme or "")
    return match.group(1) if match else None


def checks(root, online=False):
    """Every check, as (passed, what it found)."""
    results = []
    readme = read(root, "README.md")
    missing = [section for section in SECTIONS if readme is None or section not in readme]
    results.append((not missing, "README.md has all six sections" if not missing else "README.md is missing: " + ", ".join(missing)))
    url = live_url(readme)
    results.append((bool(url), f"README links the live app: {url}" if url else 'README has no "**Try it:** https://..." line'))
    video = bool(readme and re.search(r"video[^\n]*https?://", readme, re.IGNORECASE))
    results.append((video, "README links a demo video" if video else "README has no demo video link"))

    spec = read(root, "SPEC.md")
    holes = PLACEHOLDER.findall(spec or "")
    if spec is None:
        results.append((False, "SPEC.md is missing"))
    else:
        results.append((not holes, "SPEC.md is filled in" if not holes else f"SPEC.md still has {len(holes)} <placeholders> to fill in"))

    ignored = ".env" in (read(root, ".gitignore") or "").split()
    results.append((ignored, ".env is in .gitignore" if ignored else ".env is not in .gitignore"))
    leaks = [path.relative_to(root).as_posix() for path in published_files(root, ignored)
             if path.is_file() and SECRET.search(path.read_text(encoding="utf-8", errors="ignore"))]
    results.append((not leaks, "no API keys in published files" if not leaks else "API keys in: " + ", ".join(leaks)))
    locked = (root / "pyproject.toml").is_file() and (root / "uv.lock").is_file()
    results.append((locked, "pyproject.toml and uv.lock" if locked else "pyproject.toml or uv.lock is missing"))

    cases = read(root, "eval_cases.json")
    count = len(json.loads(cases)) if cases else 0
    workflows = [path.read_text(encoding="utf-8") for path in (root / ".github" / "workflows").glob("*.y*ml")]
    gated = any("run_evals.py" in workflow for workflow in workflows)
    results.append((count >= 20 and gated, f"{count} eval cases, " + ("run on every pull request" if gated else "but no workflow runs run_evals.py")))
    attacks = (root / "test_attacks.py").is_file()
    results.append((attacks, "attack tests" if attacks else "test_attacks.py is missing"))
    choice = (root / "MODEL_CHOICE.md").is_file()
    results.append((choice, "a written model choice" if choice else "MODEL_CHOICE.md is missing"))

    if online and url:
        try:  # a sleeping free server can take a minute to wake up
            status = httpx.get(url, timeout=90, follow_redirects=True).status_code
        except httpx.HTTPError as error:
            status = type(error).__name__
        results.append((status == 200, f"the live app answered {status}"))
    return results


def main(args):
    root = Path.cwd()
    results = checks(root, online="--online" in args)
    print(f"Portfolio check for {root.name}")
    for passed, found in results:
        print(f"  [{'x' if passed else ' '}] {found}")
    ready = sum(passed for passed, _ in results)
    print(f"{ready} of {len(results)} ready.")
    return ready == len(results)


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
