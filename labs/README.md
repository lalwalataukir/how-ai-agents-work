# Lab reference code for the AI engineer track

Each folder holds the finished code for one module's lab, so you can compare it with yours when you get stuck. The module pages copy their code blocks from these files, so what you copy from a page is the code tested here.

| Folder | Module | Files |
|---|---|---|
| `e01/` | [E1 · Your dev setup](https://lalwalataukir.github.io/how-ai-agents-work/eng-setup.html) | `hello.py` |
| `e02/` | [E2 · Python for AI work](https://lalwalataukir.github.io/how-ai-agents-work/eng-python.html) | `wiki_notes.py` |
| `e03/` | [E3 · Your first LLM call](https://lalwalataukir.github.io/how-ai-agents-work/eng-first-call.html) | `chat.py` |
| `e04/` | [E4 · Prompts and structured output](https://lalwalataukir.github.io/how-ai-agents-work/eng-structured.html) | `extract.py`, `article.txt` |
| `e05/` | [E5 · Tool calling](https://lalwalataukir.github.io/how-ai-agents-work/eng-tools.html) | `research_bot.py` |

Type the code yourself in your own `research-assistant` repo rather than copying this folder: you learn more from the errors.

## Tests

The `test_*.py` files run every lab offline. Websites and Claude are faked, so you need no API key or internet connection:

```
uv run --with httpx --with anthropic --with python-dotenv --with pydantic python labs/run_tests.py
```

The labs use Claude Haiku 5.5 (`claude-haiku-5-5`), the cheapest current model. Change `MODEL` (and the prices next to it) to try another.
