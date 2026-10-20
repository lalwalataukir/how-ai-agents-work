# Research assistant

An AI agent that answers research questions from Wikipedia and your own notes, with a citation for every fact.

**Try it:** https://research-assistant-xxxx.onrender.com · **Demo video (2 min):** https://youtu.be/xxxx

## What it does

Ask a question in plain words. The agent makes a plan, searches Wikipedia and your notes, reads what it needs, and answers in under 200 words with a source for each fact. It says so when it can't find an answer.

## How it works

- **Agent loop** in plain Python, with a plan, memory, call and cost limits, and approval before it saves anything
- **Retrieval** over your PDFs and notes with Chroma, citing file and page
- **Web app** in FastAPI that streams answers, with rate limits and a daily cost cap
- **Model:** Claude Haiku 5.5, chosen with evals ([MODEL_CHOICE.md](MODEL_CHOICE.md))

## Evals

20 cases in `eval_cases.json`, graded by code checks and an LLM judge. They run on every pull request and block the merge below 85%. Current score: 95%.

## Security

Tool output is marked as untrusted, tools are limited per question, files stay in their folder, answers are checked for unknown links and unread citations, and logs are redacted. Each attack has a test in `test_attacks.py`.

## Run it yourself

```
git clone https://github.com/you/research-assistant
cd research-assistant
uv sync
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
uv run uvicorn app:app --reload
```

## What I'd do next

- Keyword search alongside vector search, to fix the misses in the eval traces
- Save rate-limit and budget counts in a database, so they survive restarts
