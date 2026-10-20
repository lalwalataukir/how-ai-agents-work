# Data agent

Ask questions about a shop's sales in plain English. Claude writes SQL, the code runs it read-only and safely, and every answer shows the queries behind it, with charts when they help.

This is guided project P2 of the [AI engineer track](https://lalwalataukir.github.io/how-ai-agents-work/engineer.html). The project page walks you through it, milestone by milestone: <https://lalwalataukir.github.io/how-ai-agents-work/proj-data-agent.html>

## Set up

```
uv sync
cp .env.example .env    # then put your API key in .env
uv run make_data.py     # makes shop.db: a year of made-up sales
uv run check.py         # shows which milestones are done
```

## Milestones

1. Know the data: `describe_schema`
2. A safe SQL tool: `run_sql`
3. The agent: `run_tool` and `ask`
4. Charts: `make_chart` and `chart_tool`
5. An eval with exact answers: `grade` and `main` in `evals.py`
6. Follow-up questions: `Session.remember`

Each `TODO milestone N` comment marks code to write. After each one, run `uv run check.py N`: the checks are offline, so they cost nothing.

## Run it

```
uv run analyst.py --schema                         # what Claude knows about the data (free)
uv run analyst.py "What was revenue in March?"     # one question
uv run analyst.py                                  # a conversation, with follow-ups
uv run evals.py                                    # 10 questions with exact answers
```
