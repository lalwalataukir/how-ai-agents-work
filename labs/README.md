# Lab reference code for the AI engineer track

Each folder holds the finished code for one module's lab, so you can compare it with yours when you get stuck. The module pages copy their code blocks from these files, so what you copy from a page is the code tested here.

| Folder | Module | Files |
|---|---|---|
| `e01/` | [E1 · Your dev setup](https://lalwalataukir.github.io/how-ai-agents-work/eng-setup.html) | `hello.py` |
| `e02/` | [E2 · Python for AI work](https://lalwalataukir.github.io/how-ai-agents-work/eng-python.html) | `wiki_notes.py` |
| `e03/` | [E3 · Your first LLM call](https://lalwalataukir.github.io/how-ai-agents-work/eng-first-call.html) | `chat.py` |
| `e04/` | [E4 · Prompts and structured output](https://lalwalataukir.github.io/how-ai-agents-work/eng-structured.html) | `extract.py`, `article.txt` |
| `e05/` | [E5 · Tool calling](https://lalwalataukir.github.io/how-ai-agents-work/eng-tools.html) | `research_bot.py` |
| `e06/` | [E6 · Embeddings and RAG](https://lalwalataukir.github.io/how-ai-agents-work/eng-rag.html) | `rag.py`, `docs/library-handbook.md` |
| `e07/` | [E7 · Building agents](https://lalwalataukir.github.io/how-ai-agents-work/eng-agents.html) | `agent.py`, `agent_graph.py`, `notes_server.py` |
| `e08/` | [E8 · Tracing and evals in code](https://lalwalataukir.github.io/how-ai-agents-work/eng-evals.html) | `agent.py` (traced), `run_evals.py`, `eval_cases.json`, `evals.yml` |
| `e09/` | [E9 · Shipping it](https://lalwalataukir.github.io/how-ai-agents-work/eng-ship.html) | `agent.py` (streaming, cached), `app.py`, `static/index.html` |
| `e10/` | [E10 · Security in code](https://lalwalataukir.github.io/how-ai-agents-work/eng-security.html) | `agent.py` (hardened), `guard.py`, `test_attacks.py` |

Type the code yourself in your own `research-assistant` repo rather than copying this folder: you learn more from the errors.

In your repo all these files sit side by side in one folder. Here each module has its own, so `agent.py` appears four times: E8, E9 and E10 each hold the finished version after that module's changes.

## Tests

The `test_*.py` files run every lab offline. Websites, Claude and Langfuse are faked, so you need no API key or internet connection:

```
uv run --with-requirements labs/test-requirements.txt python labs/run_tests.py
```

The labs use Claude Haiku 5.5 (`claude-haiku-5-5`), the cheapest current model. Change `MODEL` (and the prices next to it) to try another.
