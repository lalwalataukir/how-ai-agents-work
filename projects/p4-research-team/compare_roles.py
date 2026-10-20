"""Compare models for the team's roles on the eval: how many reports pass, what each costs, how long
each takes. E11's method, applied to a team instead of one agent.

Run it with:
    uv run compare_roles.py 2    # every choice on the first 2 topics (about $0.40)
"""
import sys

import evals
import team

HAIKU, SONNET = "claude-haiku-5-5", "claude-sonnet-5-5"
CHOICES = {
    "all Haiku": {"planner": HAIKU, "worker": HAIKU, "writer": HAIKU, "critic": HAIKU},
    "Sonnet plans, writes, checks": {"planner": SONNET, "worker": HAIKU, "writer": SONNET, "critic": SONNET},
    "all Sonnet": {"planner": SONNET, "worker": SONNET, "writer": SONNET, "critic": SONNET},
}


def compare(limit=None):
    """Run the eval with each choice of roles. Returns {choice: (passed, reports, cost per report, seconds per report)}."""
    # BEGIN m6
    saved, table = dict(team.ROLES), {}
    try:
        for name, roles in CHOICES.items():
            team.ROLES.update(roles)
            rows = evals.main(limit, quiet=True)
            table[name] = (sum(r["passed"] for r in rows), len(rows), sum(r["cost"] for r in rows) / len(rows),
                           sum(r["seconds"] for r in rows) / len(rows))
    finally:
        team.ROLES.update(saved)  # put the real choice back, whatever happened
    return table
    # END m6
    #> # TODO milestone 6: for each choice, update team.ROLES, run evals.main(limit, quiet=True), and record
    #> # how many passed, how many ran, and the cost and seconds per report. Restore team.ROLES at the end.
    #> raise NotImplementedError("milestone 6: compare")


def main(limit=None):
    print(f"{'Roles':<30} {'Passed':>8} {'$ / report':>11} {'s / report':>11}")
    for name, (passed, total, cost, seconds) in compare(limit).items():
        print(f"{name:<30} {f'{passed} of {total}':>8} {cost:>11.4f} {seconds:>11.1f}")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 2)
