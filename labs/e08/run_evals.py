"""E8 lab: run the eval cases against the agent, score them, and fail when the score is too low.

Run it with:
    uv run run_evals.py      # every case
    uv run run_evals.py 3    # the first 3 cases, for a quick, cheap check
"""
import json
import re
import sys
from pathlib import Path

import anthropic
from langfuse import observe, propagate_attributes
from pydantic import BaseModel

import agent

MIN_SCORE = 0.85  # below this the run fails: set it just under your current score
JUDGE_MODEL = "claude-haiku-5-5"  # a stronger judge costs more and agrees with people more often
CASES = Path(__file__).parent / "eval_cases.json"
REPORT = Path(__file__).parent / "eval_report.json"
JUDGE = """You grade a research assistant's answer to a question.

<question>{question}</question>
<reference>{reference}</reference>
<answer>{answer}</answer>

Pass the answer only if all of these are true:
- It answers the question. When the reference says the answer can't be known, it says so instead of guessing.
- Nothing in it contradicts the reference.
- Every fact in it has a citation in square brackets.
Give your reason in one sentence, then your verdict."""


class Verdict(BaseModel):
    reason: str  # first, so the judge explains before it decides
    passed: bool


def code_checks(case, answer):
    """Checks that code can do exactly: free, instant, and the same every time."""
    problems = []
    for words in case["must_include"]:  # "1955|1956" means either one will do
        if not any(word.lower() in answer.lower() for word in words.split("|")):
            problems.append(f"doesn't mention {words}")
    if case["expect"] == "answer" and not re.search(r"\[[^\]]+\]", answer):
        problems.append("no citation")
    if len(answer.split()) > 200:
        problems.append("over 200 words")
    if answer.startswith("Stopped"):
        problems.append("hit a limit")
    return problems


def judge(case, answer):
    """An LLM judge for what code can't check: is it right, and does it say so when it doesn't know?"""
    prompt = JUDGE.format(question=case["question"], reference=case["reference"], answer=answer)
    response = agent.client.messages.parse(
        model=JUDGE_MODEL, max_tokens=1000, output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}], output_format=Verdict,
    )
    usage = response.usage
    return response.parsed_output, (usage.input_tokens * agent.PRICE_IN + usage.output_tokens * agent.PRICE_OUT) / 1_000_000


@observe(name="eval-case")
def run_case(case):
    """Run one case through the agent, then grade it: code checks first, the judge only if they pass."""
    with propagate_attributes(tags=["eval"], metadata={"case": case["id"]}):  # find eval runs in Langfuse
        for event in agent.steps(case["question"], [], approve=lambda name, args: False):  # evals never save notes
            pass  # the last event is "done", with the answer
        problems = code_checks(case, event["answer"])
        cost = event["cost"]
        if not problems:
            verdict, judge_cost = judge(case, event["answer"])
            cost += judge_cost
            if not verdict.passed:
                problems.append("judge: " + verdict.reason)
        agent.langfuse.score_current_trace(name="passed", value=float(not problems), comment="; ".join(problems) or None)
    return {"id": case["id"], "passed": not problems, "problems": problems, "answer": event["answer"],
            "calls": event["calls"], "tools": event["tools"], "cost": round(cost, 6)}


def main(limit=None):
    cases = json.loads(CASES.read_text(encoding="utf-8"))[:limit]
    results = []
    for n, case in enumerate(cases, 1):
        try:
            result = run_case(case)
        except anthropic.APIError as error:  # one failed request fails that case, not the whole run
            result = {"id": case["id"], "passed": False, "problems": [f"API error: {error}"], "calls": 0, "cost": 0.0}
        mark = "pass" if result["passed"] else "FAIL"
        print(f"{n:2} {mark}  {case['id']:<16} {result['calls']:2} calls  ${result['cost']:.5f}  {'; '.join(result['problems'])}")
        results.append(result)

    passed = sum(result["passed"] for result in results)
    score = passed / len(results)
    cost = sum(result["cost"] for result in results)
    REPORT.write_text(json.dumps({"score": score, "min_score": MIN_SCORE, "results": results}, indent=2), encoding="utf-8")
    print(f"\nScore {passed}/{len(results)} = {score:.0%} (minimum {MIN_SCORE:.0%}). This run cost ${cost:.4f}.")
    agent.langfuse.flush()  # send any traces still waiting before the program ends
    return score >= MIN_SCORE


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    sys.exit(0 if main(limit) else 1)  # exit code 1 tells GitHub Actions the check failed
