# Agent Field Guides

Interactive guides for product managers, built around one running example: a research-assistant agent.

**Home page:** https://lalwalataukir.github.io/how-ai-agents-work/

| Module | Live link |
|---|---|
| **1 · How AI agents work**: ideation, design, build, test and ship, with a step-by-step simulated agent demo, quizzes and a cheat sheet | https://lalwalataukir.github.io/how-ai-agents-work/how-ai-agents-work.html |
| **2 · LangChain, LangGraph & Langfuse**: the three tools at a glance, with a clickable simulated graph run and a Langfuse-style trace | https://lalwalataukir.github.io/how-ai-agents-work/langchain-langgraph-langfuse.html |
| **3 · LangChain in depth**: models, prompts, tools, retrieval, chains and agents, with a chain workbench demo | https://lalwalataukir.github.io/how-ai-agents-work/langchain.html |
| **4 · LangGraph in depth**: state, edges, retries, checkpoints, human-in-the-loop and time travel, with a crash/resume/fork demo | https://lalwalataukir.github.io/how-ai-agents-work/langgraph.html |
| **5 · Langfuse in depth**: traces, cost, latency, prompt management and evaluation, with a debug-a-complaint demo | https://lalwalataukir.github.io/how-ai-agents-work/langfuse.html |

**Demo lab:** https://lalwalataukir.github.io/how-ai-agents-work/demo-lab.html has the LangChain, LangGraph and Langfuse demos in one page, with tabs. Each tab loads the demo from its module page, so there's only one copy of each demo.

Everything in the demos is a scripted simulation. No AI model, search engine, framework or tracing service is contacted, and the example addresses are made up. These pages are independent explainers and aren't affiliated with LangChain, LangGraph, LangSmith or Langfuse.

The HTML files here are generated from the source pages by running `node serve.js --build`.
