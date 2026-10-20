"""Score the team on 5 topics: how much of each report is cited and how much of the topic it covers,
checked by code, whether it sticks to its findings, checked by a judge, and what it cost.

Run it with:
    uv run evals.py      # all 5 topics, about $0.10 with the default roles
    uv run evals.py 2    # the first 2
"""
import json
import re
import sys
from pathlib import Path

from langfuse import observe, propagate_attributes
from pydantic import BaseModel

import team

TOPICS = json.loads((Path(__file__).parent / "eval_topics.json").read_text(encoding="utf-8"))
JUDGE_MODEL = "claude-haiku-5-5"
MIN_CITED, MIN_MENTIONS = 0.9, 0.75  # a report passes with these, and the judge's yes
JUDGE = """You check a research report against the findings it was written from.

<findings>{findings}</findings>
<report>{report}</report>

Pass it only if every claim in the report is supported by the findings, and nothing in it
contradicts them. Give your reason in one sentence, then your verdict."""


class Verdict(BaseModel):
    reason: str  # first, so the judge explains before it decides
    passed: bool


def cited_share(report):
    """The share of the body's paragraphs (not headings) that cite at least one source."""
    # BEGIN m5
    paragraphs = [p for p in team.body_of(report).split("\n\n") if p.strip() and not p.lstrip().startswith("#")]
    return sum(bool(re.search(r"\[\d+\]", p)) for p in paragraphs) / len(paragraphs) if paragraphs else 0.0
    # END m5
    #> # TODO milestone 5: split the body into paragraphs, leave out headings, and return the share with an [n].
    #> raise NotImplementedError("milestone 5: cited_share")


def mentions(report, terms):
    """The share of terms the report mentions. "sunshield|sun shield" means either will do."""
    # BEGIN m5
    text = report.lower()
    return sum(any(word.lower() in text for word in term.split("|")) for term in terms) / len(terms)
    # END m5
    #> # TODO milestone 5: for each term, check whether any of its |-separated words is in the report (any case).
    #> raise NotImplementedError("milestone 5: mentions")


def judge(result):
    """Does the report stick to its findings? Returns the verdict, and what the judge cost."""
    findings = "\n\n".join(f"Q: {f.question}\nA: {f.answer}" for f in result.findings)
    response = team.client.messages.parse(
        model=JUDGE_MODEL, max_tokens=1000, output_config={"effort": "low"}, output_format=Verdict,
        messages=[{"role": "user", "content": JUDGE.format(findings=findings, report=result.report)}],
    )
    price_in, price_out = team.PRICES[JUDGE_MODEL]
    return response.parsed_output, (response.usage.input_tokens * price_in + response.usage.output_tokens * price_out) / 1_000_000


@observe(name="eval-topic")
def run_topic(case):
    """One topic: run the team, grade the report, and score the trace in Langfuse."""
    # BEGIN m5
    with propagate_attributes(tags=["eval"], metadata={"topic": case["topic"]}):  # find eval runs in Langfuse
        result = team.run(case["topic"])
        cited, mentioned = cited_share(result.report), mentions(result.report, case["must_mention"])
        verdict, judge_cost = judge(result)
        passed = cited >= MIN_CITED and mentioned >= MIN_MENTIONS and verdict.passed
        team.langfuse.score_current_trace(name="passed", value=float(passed), comment=verdict.reason)
    return {"topic": case["topic"], "passed": passed, "cited": cited, "mentions": mentioned, "judge": verdict.passed,
            "reason": verdict.reason, "cost": result.costs.total() + judge_cost, "seconds": result.seconds}
    # END m5
    #> # TODO milestone 5: run the team on the topic, grade it with cited_share, mentions and judge, score
    #> # the trace with team.langfuse.score_current_trace, and return a row like the one main prints.
    #> raise NotImplementedError("milestone 5: run_topic")


def main(limit=None, quiet=False):
    rows = [run_topic(case) for case in TOPICS[:limit]]
    team.langfuse.flush()
    if not quiet:
        for row in rows:
            print(f"  [{'x' if row['passed'] else ' '}] {row['topic'][:52]:<52} cited {row['cited']:>4.0%} · "
                  f"topic {row['mentions']:>4.0%} · judge {'yes' if row['judge'] else 'no ':<3} · ${row['cost']:.4f} · {row['seconds']:>4.1f} s")
        print(f"{sum(r['passed'] for r in rows)} of {len(rows)} passed. ${sum(r['cost'] for r in rows):.4f} in all, "
              f"{sum(r['seconds'] for r in rows) / len(rows):.1f} s a report.")
    return rows


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else None)
