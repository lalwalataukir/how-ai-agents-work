# Agent Field Guides

Interactive guides for product managers, built around one running example: a research-assistant agent.

**Home page:** https://lalwalataukir.github.io/how-ai-agents-work/

| Module | Live link |
|---|---|
| **1 · How AI agents work**: ideation, design, build, test and ship, with a step-by-step simulated agent demo (including a prompt-injection scenario), a downloadable spec template, quizzes and a cheat sheet | https://lalwalataukir.github.io/how-ai-agents-work/how-ai-agents-work.html |
| **2 · LangChain, LangGraph & Langfuse**: the three tools at a glance, with a clickable simulated graph run, a Langfuse-style trace, and a decision guide covering alternatives and cost | https://lalwalataukir.github.io/how-ai-agents-work/langchain-langgraph-langfuse.html |
| **3 · LangChain in depth**: models, prompts, tools and MCP, retrieval, chains, memory and agents, with a chain workbench and a retrieval tuner | https://lalwalataukir.github.io/how-ai-agents-work/langchain.html |
| **4 · LangGraph in depth**: state, edges, retries, checkpoints, human-in-the-loop, time travel and testing, with a crash/resume/fork demo | https://lalwalataukir.github.io/how-ai-agents-work/langgraph.html |
| **5 · Langfuse in depth**: traces, cost, latency, prompt management and governance, and evaluation, with a debug-a-complaint demo | https://lalwalataukir.github.io/how-ai-agents-work/langfuse.html |
| **6 · Metrics for a compliant wealth AI bot**: 7 metric categories with P0/P1/P2 metrics and their definitions, a spot-the-breach demo, sampling maths, Langfuse wiring, an incident runbook and a P0 launch checklist | https://lalwalataukir.github.io/how-ai-agents-work/metrics.html |
| **7 · Shipping an agent**: staged rollout, designing for trust, unit economics and pricing, build or buy, and a six-week case study, with a rollout simulator | https://lalwalataukir.github.io/how-ai-agents-work/ship.html |
| **8 · Context engineering**: what goes in the context window, writing instructions, tool definitions, retrieval vs memory vs history, long runs and compaction, prompt caching and context failures, with a context-budget demo | https://lalwalataukir.github.io/how-ai-agents-work/context.html |
| **9 · Agent security**: prompt injection, least privilege, containment, MCP supply chain, data protection, red-teaming and a threat model, with a break-the-agent demo | https://lalwalataukir.github.io/how-ai-agents-work/security.html |
| **10 · Evals in practice**: error analysis, building a dataset, code checks, LLM judges and people, judge calibration, pass@k and pass^k, CI gates and online evals, comparing versions and a weekly ritual, with a grade-the-grader demo | https://lalwalataukir.github.io/how-ai-agents-work/evals.html |
| **Reference**: every glossary term from the modules, searchable, plus further reading | https://lalwalataukir.github.io/how-ai-agents-work/reference.html |

## AI engineer track

A hands-on track for beginners who want to build agents, not just understand them. Each module has concepts, an in-browser demo, and a lab you run on your own laptop. Every lab grows one project: the research assistant, built for real.

| Module | Live link |
|---|---|
| **Track home**: the roadmap of all 12 modules, what you need before you start, and your progress | https://lalwalataukir.github.io/how-ai-agents-work/engineer.html |
| **E1 · Your dev setup**: the terminal, Python with uv, VS Code, git and GitHub, and reading errors, with a terminal-practice demo and a lab that puts your first program on GitHub | https://lalwalataukir.github.io/how-ai-agents-work/eng-setup.html |
| **E2 · Python for AI work**: values, lists and dicts, functions and loops, files and JSON, errors, web APIs and pairing with an AI assistant, with a predict-the-output demo and a lab that saves Wikipedia notes | https://lalwalataukir.github.io/how-ai-agents-work/eng-python.html |
| **E3 · Your first LLM call**: API keys, the Messages API, system prompts and effort, tokens and cost, streaming, and errors and retries, with a request-builder demo and a chatbot lab that prints its cost | https://lalwalataukir.github.io/how-ai-agents-work/eng-first-call.html |
| **E4 · Prompts and structured output**: templates, clear instructions, few-shot examples, structured outputs with Pydantic, and check-and-retry, with a schema-check demo and an article-extractor lab | https://lalwalataukir.github.io/how-ai-agents-work/eng-structured.html |
| **E5 · Tool calling**: defining tools, the tool-use loop by hand, running tools safely, and what loops cost, with a loop-stepper demo and a Wikipedia research-bot lab | https://lalwalataukir.github.io/how-ai-agents-work/eng-tools.html |
| **E6 · Embeddings and RAG**: embeddings, chunking, vector search with Chroma, citations and failure modes, with a chunk-and-retrieve demo on real embedding distances and a lab that answers questions over your own documents | https://lalwalataukir.github.io/how-ai-agents-work/eng-rag.html |
| **E7 · Building agents**: planning, memory and state, stop conditions, human approval, LangGraph and MCP, with an agent-trace demo and a lab that builds the research agent in plain Python and LangGraph, plus an MCP server | https://lalwalataukir.github.io/how-ai-agents-work/eng-agents.html |
| **E8 · Tracing and evals in code**: Langfuse tracing, an eval set in code, code checks and an LLM judge, and evals in GitHub Actions, with a CI-gate demo and a lab that blocks pull requests when the score drops | https://lalwalataukir.github.io/how-ai-agents-work/eng-evals.html |
| **E9 · Shipping it**: FastAPI, streaming, rate limits, cost caps, prompt caching, latency and free hosting, with a latency-and-cost demo and a lab that deploys the agent to Render | https://lalwalataukir.github.io/how-ai-agents-work/eng-ship.html |
| **E10 · Security in code**: input handling, prompt-injection defences, tool permissions, sandboxing, and secrets and personal data, with a break-the-agent demo and a lab that writes every attack as a test | https://lalwalataukir.github.io/how-ai-agents-work/eng-security.html |

The finished code for each lab is in [`labs/`](labs/), with offline tests: `uv run --with-requirements labs/test-requirements.txt python labs/run_tests.py`.

**Demo lab:** https://lalwalataukir.github.io/how-ai-agents-work/demo-lab.html has the LangChain, LangGraph and Langfuse demos in one page, with tabs. Each tab loads the demo from its module page, so there's only one copy of each demo.

Everything in the demos is a scripted simulation. No AI model, search engine, framework or tracing service is contacted, and the example addresses are made up. These pages are independent explainers and aren't affiliated with LangChain, LangGraph, LangSmith or Langfuse.

The HTML files here are generated from the source pages by running `node serve.js --build`.

**Search:** every page has a Search button (shortcut `/` or `Ctrl+K`) that searches all modules and the glossary. It's powered by `search.js` and the generated `search-index.js`. After changing any page's content, run `python3 build-search.py` to rebuild the index.

**Tool links:** every mention of a tool (LangChain, LangGraph, Langfuse, MCP and others) links to its official docs, with a hover card. `tool-links.js` does this on every page. To add a tool or change a link, edit the `TOOLS` list at the top of that file.
