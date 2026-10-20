"""Score the agent on 10 questions with exact answers, checked by code.

Run it with:
    uv run evals.py      # all 10 questions
    uv run evals.py 3    # the first 3
"""
import json
import sys
from pathlib import Path

import analyst

CASES = json.loads((Path(__file__).parent / "eval_questions.json").read_text(encoding="utf-8"))


def grade(answer, case):
    """(passed, why) for one answer. The value must be within 0.5% of the right number (or 0.01),
    and the answer must name the thing asked for, when the case says what that is."""
    # BEGIN m5
    if answer.value is None:
        return False, "no value"
    if abs(answer.value - case["value"]) > max(0.01, abs(case["value"]) * 0.005):
        return False, f"value {answer.value}, expected {case['value']}"
    if "contains" in case and case["contains"].lower() not in answer.answer.lower():
        return False, f"doesn't mention {case['contains']}"
    return True, "right"
    # END m5
    #> # TODO milestone 5: compare answer.value with case["value"], allowing 0.5% (or at least 0.01),
    #> # and check answer.answer mentions case["contains"] when the case has it.
    #> raise NotImplementedError("milestone 5: grade")


def main(limit=None):
    """Ask every question with a fresh memory, grade it, and print a line each and a summary."""
    # BEGIN m5
    cost, passed = analyst.Cost(), 0
    for n, case in enumerate(CASES[:limit], 1):
        result = analyst.ask(case["question"], [], analyst.DB, cost)
        ok, why = grade(result.answer, case)
        passed += ok
        print(f"  [{'x' if ok else ' '}] {n:>2}. {case['question']}  ({why}; SQL queries: {len(result.queries)})")
    total = len(CASES[:limit])
    print(f"{passed} of {total} right ({passed / total:.0%}). {cost.calls} model calls, ${cost.dollars():.4f}")
    return passed, total
    # END m5
    #> # TODO milestone 5: for each case, call analyst.ask with an empty memory (and one shared Cost),
    #> # grade it, print a line per question, then "N of M right" with the calls and cost.
    #> raise NotImplementedError("milestone 5: evals main")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
