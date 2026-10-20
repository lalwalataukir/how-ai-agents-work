# Code reviewer

A command-line tool that reviews a code change with Claude. Each problem it finds comes with the file, the line, a severity and a fix, and it can stop a commit when it finds something serious.

This is guided project P1 of the [AI engineer track](https://lalwalataukir.github.io/how-ai-agents-work/engineer.html). The project page walks you through it, milestone by milestone: <https://lalwalataukir.github.io/how-ai-agents-work/proj-code-review.html>

## Set up

```
uv sync
cp .env.example .env    # then put your API key in .env
uv run check.py         # shows which milestones are done
```

## Milestones

1. Read the diff: `parse_diff` and `format_change`
2. A structured review: `Finding`, `Review` and `ask`
3. Check every finding: `check` and `review`
4. Let it read files: `read_file` and `run_tool`
5. Use it every day: `git_diff`, `to_markdown`, `should_block` and `main`

Each `TODO milestone N` comment in `reviewer.py` marks code to write. After each one, run `uv run check.py N`: the checks are offline, so they cost nothing.

## Run it

```
uv run reviewer.py sample/changes.diff --repo sample --prompt   # what Claude will see (free)
uv run reviewer.py sample/changes.diff --repo sample            # review the sample change
uv run score.py                                                 # how many of its 5 planted bugs it finds
uv run reviewer.py --staged                                     # review what you're about to commit
```
