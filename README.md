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
| **9 · Agent security**: prompt injection, least privilege, containment, MCP supply chain, data protection, red-teaming and a threat model, with a break-the-agent demo | https://lalwalataukir.github.io/how-ai-agents-work/security.html |
| **Reference**: every glossary term from the modules, searchable, plus further reading | https://lalwalataukir.github.io/how-ai-agents-work/reference.html |

**Demo lab:** https://lalwalataukir.github.io/how-ai-agents-work/demo-lab.html has the LangChain, LangGraph and Langfuse demos in one page, with tabs. Each tab loads the demo from its module page, so there's only one copy of each demo.

Everything in the demos is a scripted simulation. No AI model, search engine, framework or tracing service is contacted, and the example addresses are made up. These pages are independent explainers and aren't affiliated with LangChain, LangGraph, LangSmith or Langfuse.

The HTML files here are generated from the source pages by running `node serve.js --build`.

**Search:** every page has a Search button (shortcut `/` or `Ctrl+K`) that searches all modules and the glossary. It's powered by `search.js` and the generated `search-index.js`. After changing any page's content, run `python3 build-search.py` to rebuild the index.

**Tool links:** every mention of a tool (LangChain, LangGraph, Langfuse, MCP and others) links to its official docs, with a hover card. `tool-links.js` does this on every page. To add a tool or change a link, edit the `TOOLS` list at the top of that file.
