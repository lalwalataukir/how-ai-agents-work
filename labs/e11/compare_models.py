"""E11 lab: run the eval set on several models, and compare quality, cost and speed.

Run it with:
    uv run compare_models.py      # every case on every model
    uv run compare_models.py 5    # the first 5 cases: a quick, cheap look
"""
import json
import statistics
import sys
import time
from pathlib import Path

import anthropic

import agent
import run_evals

# Dollars per million tokens: input, output, and input read from the cache.
# Writing to the cache costs 1.25 times the input price.
MODELS = {
    "claude-haiku-5-5": (0.10, 0.50, 0.01),
    "claude-sonnet-5-5": (2.00, 10.00, 0.20),
    "claude-opus-5-5": (4.00, 20.00, 0.20),
}
REPORT = Path(__file__).parent / "model_report.json"


def cost_of(model, run):
    """What one run cost at this model's prices, from the token counts the agent reports."""
    price_in, price_out, price_read = MODELS[model]
    dollars = (run["tokens_in"] + 1.25 * run["cache_written"]) * price_in + run["cache_read"] * price_read
    return (dollars + run["tokens_out"] * price_out) / 1_000_000


def evaluate(model, cases):
    """Run every case on one model. The judge stays the same, so only the model changes."""
    agent.MODEL = model
    agent.PRICE_IN, agent.PRICE_OUT = MODELS[model][:2]  # so the agent's own cost limit uses the right prices
    passed, costs, seconds = 0, [], []
    for case in cases:
        start = time.perf_counter()
        try:
            for event in agent.steps(case["question"], [], approve=lambda name, args: False):
                pass  # the last event is "done"
            problems = run_evals.code_checks(case, event["answer"])
            if not problems:
                verdict, _ = run_evals.judge(case, event["answer"])
                problems = [] if verdict.passed else ["judge: " + verdict.reason]
            costs.append(cost_of(model, event))
        except anthropic.APIError as error:
            problems = [f"API error: {error}"]
        seconds.append(time.perf_counter() - start)
        passed += not problems
        print(f"  {model:<18} {case['id']:<16} {'pass' if not problems else 'FAIL'}  {seconds[-1]:5.1f} s")
    return {"model": model, "score": passed / len(cases),
            "per_1000": round(1000 * statistics.mean(costs), 3) if costs else None,
            "median_seconds": round(statistics.median(seconds), 1)}


def main(limit=None):
    cases = json.loads(run_evals.CASES.read_text(encoding="utf-8"))[:limit]
    rows = [evaluate(model, cases) for model in MODELS]
    print(f"\n{'model':<18} {'score':>6} {'per 1,000 questions':>20} {'median time':>12}")
    for row in rows:
        cost = f"${row['per_1000']:.3f}" if row["per_1000"] is not None else "-"
        print(f"{row['model']:<18} {row['score']:>6.0%} {cost:>20} {row['median_seconds']:>10.1f} s")
    good_enough = [row for row in rows if row["score"] >= run_evals.MIN_SCORE and row["per_1000"] is not None]
    best = min(good_enough, key=lambda row: row["per_1000"]) if good_enough else None
    print(f"\nCheapest model at or above {run_evals.MIN_SCORE:.0%}: {best['model'] if best else 'none'}")
    REPORT.write_text(json.dumps({"cases": len(cases), "min_score": run_evals.MIN_SCORE, "models": rows}, indent=2), encoding="utf-8")
    return best


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
