"""Score the reviewer on the sample change: how many of its 5 planted bugs does it find?

Run it with:
    uv run score.py
"""
import json
from pathlib import Path

import reviewer

SAMPLE = Path(__file__).parent / "sample"


def match(findings, planted):
    """Which planted bugs some finding points at, and which findings point at none."""
    found = [bug for bug in planted
             if any(f.file == bug["file"] and bug["lines"][0] <= f.line <= bug["lines"][1] for f in findings)]
    extra = [f for f in findings
             if not any(f.file == bug["file"] and bug["lines"][0] <= f.line <= bug["lines"][1] for bug in planted)]
    return found, extra


def main():
    planted = json.loads((SAMPLE / "planted.json").read_text(encoding="utf-8"))
    changes = reviewer.parse_diff((SAMPLE / "changes.diff").read_text(encoding="utf-8"))
    result, cost = reviewer.review(changes, SAMPLE)
    found, extra = match(result.findings, planted)
    for bug in planted:
        print(f"  [{'x' if bug in found else ' '}] {bug['file']}: {bug['bug']}")
    for f in extra:
        print(f"  [+] {f.file}:{f.line} ({f.severity}) {f.issue}")
    print(f"Found {len(found)} of {len(planted)} planted bugs, plus {len(extra)} other finding(s). "
          f"{cost.calls} model call(s), ${cost.dollars():.4f}")


if __name__ == "__main__":
    main()
