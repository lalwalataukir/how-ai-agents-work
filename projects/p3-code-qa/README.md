# Code Q&A

Ask questions about a codebase and get answers that cite the file and lines they come from. It splits code into functions with Python's `ast`, finds the right ones with keyword and vector search together, and runs as a command, a streaming web app and an MCP server for Claude Code.

This is guided project P3 of the [AI engineer track](https://lalwalataukir.github.io/how-ai-agents-work/engineer.html). The project page walks you through it, milestone by milestone: <https://lalwalataukir.github.io/how-ai-agents-work/proj-code-qa.html>

## Set up

```
uv sync
cp .env.example .env    # then put your API key in .env
uv run check.py         # shows which milestones are done
```

`tinyshop/` is the sample codebase the questions are about. Set `CODE_ROOT` in `.env` to ask about another one.

## Milestones

1. Split code into chunks: `chunk_python` and `chunk_repo`
2. Keyword and vector search: `words`, `Keyword.search` and `fuse`
3. The agent: `run_tool`, `check_citations` and `steps`
4. Guards: `safe_path`, `untrusted`, `limit_reached` and `clean_question` in `guard.py`
5. A web app with limits: `check_limits` and `ask` in `app.py`
6. An MCP server: `search_code` and `read_lines` in `mcp_server.py`

Each `TODO milestone N` comment marks code to write. After each one, run `uv run check.py N`: the checks are offline, so they cost nothing.

## Run it

```
uv run qa.py chunks                                  # how the code splits (free)
uv run qa.py search "where are passwords hashed"     # what search finds (free)
uv run eval_search.py                                # recall@5 for keyword, vector and hybrid search (free)
uv run qa.py ask "How does login lock an account?"
uv run uvicorn app:app --reload                      # the web app, at http://127.0.0.1:8000
```
