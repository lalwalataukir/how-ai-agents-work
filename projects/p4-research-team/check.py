"""Check your project, milestone by milestone. Claude is faked, so no API key or internet is needed.

Run it with:
    uv run check.py      # check every milestone
    uv run check.py 3    # check milestones 1 to 3
"""
import os
import re
import sys
import textwrap
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # the tests never call Claude
ROOT = Path(__file__).parent
TESTS = ROOT / "tests"
sys.path[:0] = [str(ROOT), str(TESTS)]


def milestones():
    """(number, title, test file) for each tests/test_m<number>_*.py, in order."""
    found = []
    for path in TESTS.glob("test_m*_*.py"):
        number = int(re.match(r"test_m(\d+)_", path.name)[1])
        title = path.read_text(encoding="utf-8").split('"""')[1].split(":", 1)[-1].strip()
        title = title[:1].upper() + title[1:]
        found.append((number, title, path))
    return sorted(found)


def last_line(trace):
    """The line of a traceback that says what went wrong, shortened."""
    line = trace.strip().splitlines()[-1]
    return line if len(line) <= 160 else line[:157] + "..."


def todo_left(number):
    """True if a "TODO milestone <number>" comment is still in your code."""
    return any(f"TODO milestone {number}:" in path.read_text(encoding="utf-8", errors="ignore")
               for path in ROOT.glob("*.py") if path.name != "check.py")


def check(number, path):
    """Run one milestone's tests. Returns (status, details, first problem): status is done, todo or failing."""
    try:
        tests = unittest.defaultTestLoader.loadTestsFromName(path.stem)
    except Exception as error:  # for example a SyntaxError in your code
        status = "todo" if isinstance(error, NotImplementedError) or todo_left(number) else "failing"
        return status, "not started" if status == "todo" else "the checks couldn't start", f"{type(error).__name__}: {error}"
    result = unittest.TestResult()
    tests.run(result)
    problems = result.errors + result.failures
    if not problems and result.testsRun:
        return "done", f"{result.testsRun} checks pass", ""
    test, trace = problems[0]
    first = f"{getattr(test, '_testMethodName', '')}: {last_line(trace)}"
    if todo_left(number) or any("NotImplementedError" in trace for _, trace in problems):
        return "todo", "not started", first
    return "failing", f"{len(problems)} of {result.testsRun} checks fail", first


def main(args):
    upto = int(args[0]) if args else None
    marks = {"done": "[x]", "todo": "[ ]", "failing": "[!]"}
    done, checked, first_open = 0, 0, None
    for number, title, path in milestones():
        if upto and number > upto:
            break
        status, details, first = check(number, path)
        checked += 1
        print(f"  {marks[status]} {number}  {title}: {details}")
        if status == "done":
            done += 1
        elif first_open is None:  # the milestone to work on now: say what fails, and how to fix it
            first_open = number
            print(textwrap.fill(first, 100, initial_indent=" " * 9, subsequent_indent=" " * 11))
            hint = getattr(sys.modules.get(path.stem), "HINT", "")
            if hint:
                print(textwrap.fill("Hint: " + hint, 100, initial_indent=" " * 9, subsequent_indent=" " * 15))
    print(f"{done} of {checked} milestones done." + (f" Next: milestone {first_open}." if first_open else ""))
    return first_open is None


if __name__ == "__main__":
    sys.exit(0 if main(sys.argv[1:]) else 1)
