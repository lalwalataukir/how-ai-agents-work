# Guided projects

The finished code for the AI engineer track's [guided projects](https://lalwalataukir.github.io/how-ai-agents-work/eng-projects.html). Learners download a starter zip from each project's page; the starters are built from the code here.

| Folder | Project | Starter |
|---|---|---|
| `p1-code-review/` | [P1 · AI code reviewer](https://lalwalataukir.github.io/how-ai-agents-work/proj-code-review.html) | `p1-code-review-starter.zip` |
| `p2-data-agent/` | [P2 · Data-analysis agent](https://lalwalataukir.github.io/how-ai-agents-work/proj-data-agent.html) | `p2-data-agent-starter.zip` |
| `p3-code-qa/` | [P3 · Codebase Q&A assistant](https://lalwalataukir.github.io/how-ai-agents-work/proj-code-qa.html) | `p3-code-qa-starter.zip` |

## How a starter is made

Each project's code marks what the learner writes in each milestone:

```python
def check(review, changes):
    # BEGIN m3
    ...the finished code...
    # END m3
    #> # TODO milestone 3: what to write
    #> return []
```

`build.py` gives the starter the `#>` lines (or `raise NotImplementedError` when there are none) and the finished code everything else. The starter runs from the start, and each milestone makes it do more.

```
python projects/build.py          # rebuild the starter zips after changing a project
python projects/build.py --check  # fail if a zip is out of date
```

`check.py` is the checker every project ships with. It runs `tests/test_m<N>_*.py` for each milestone; Claude is faked in the tests, so checking needs no API key or network.

## Tests

`test_projects.py` checks the starters themselves: each zip is up to date, and after N milestones the checker says exactly milestones 1 to N are done. It also sends each project's requests through the real Anthropic SDK with only the network faked. These run with the lab tests:

```
uv run --with-requirements labs/test-requirements.txt python labs/run_tests.py
```
