# Research team

A team of agents that writes a short, cited research report. A planner splits the topic into questions, workers research them in parallel on Wikipedia within their own budgets, a writer drafts the report with numbered sources, and a critic sends it back once if anything is unsupported or uncited. Every run is one trace in Langfuse, and an eval measures each report.

This is guided project P4 of the [AI engineer track](https://lalwalataukir.github.io/how-ai-agents-work/engineer.html). The project page walks you through it, milestone by milestone: <https://lalwalataukir.github.io/how-ai-agents-work/proj-research-team.html>

## Set up

```
uv sync
cp .env.example .env    # then put your API key in .env, and your Langfuse keys from E8
uv run check.py         # shows which milestones are done
```

## Milestones

1. The planner: `plan`
2. Workers, in parallel: `research` and `research_all`
3. The writer: `number_sources` and `write`
4. The critic, and the whole run: `citation_problems`, `critique` and `run`
5. Traces and evals: `cited_share`, `mentions` and `run_topic` in `evals.py`
6. A model for each role: `compare` in `compare_roles.py`, then `ROLES`

Each `TODO milestone N` comment marks code to write. After each one, run `uv run check.py N`: the checks are offline, so they cost nothing.

## Run it

```
uv run team.py "How the James Webb Space Telescope works"   # a report in reports/
uv run evals.py                                              # 5 topics, graded
uv run compare_roles.py 2                                    # models per role, compared on 2 topics
```
