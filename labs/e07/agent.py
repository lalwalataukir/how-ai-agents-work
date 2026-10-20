"""E7 lab: the research assistant as an agent. It makes a plan, searches your notes and
Wikipedia, remembers the conversation, stops at its limits, and asks before it saves anything.

Run it with:
    uv run agent.py
"""
import json
import re
from datetime import date
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

from rag import index_file, search  # E6: your notes
from research_bot import TOOLS as WIKI_TOOLS, run_tool as run_wiki_tool  # E5: Wikipedia

load_dotenv()

MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10, 0.50  # dollars per million tokens, for this model
MAX_CALLS = 10   # stop condition: most model calls for one question
MAX_COST = 0.02  # stop condition: most dollars for one question
NOTES = Path(__file__).parent / "notes"  # save_note writes Markdown files here
SYSTEM = (
    "You are a research assistant. Use the tools to search the user's notes and Wikipedia, and follow "
    "the plan you're given, changing it if a tool shows it won't work. Cite every fact: [Page title] "
    "for Wikipedia, [file, page N] for the user's notes. Save a note only when the user asks you to. "
    "If you can't find the answer, say so. Answer in at most 200 words."
)
PLANNER = (
    "You plan the work of a research assistant. Its tools: search_notes (the user's own notes and PDFs), "
    "search_wikipedia and read_page (Wikipedia), and save_note (only when the user asks to save something). "
    "Write a plan of 1 to 4 short steps for the latest request. Don't answer it."
)

TOOLS = WIKI_TOOLS + [
    {
        "name": "search_notes",
        "description": "Search the user's own notes and PDFs. Returns up to 4 passages, each with its file "
                       "and page. Use it first for anything the user may have notes on.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look for, in plain words"}},
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "save_note",
        "description": "Save a note for the user as a Markdown file. Only use it when the user asks to save "
                       "something. The user approves every save.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "A short title"},
                "text": {"type": "string", "description": "The note, with its citations"},
            },
            "required": ["title", "text"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
ALL_TOOLS = [tool["name"] for tool in TOOLS]
NEEDS_APPROVAL = {"save_note"}  # tools that change something: a person says yes first

client = anthropic.Anthropic()


class Plan(BaseModel):
    steps: list[str]


def make_plan(question, memory):
    """Ask for a short plan before any tool runs. Returns the steps and the call's token usage."""
    response = client.messages.parse(
        model=MODEL, max_tokens=1000, system=PLANNER, output_config={"effort": "low"},
        messages=memory + [{"role": "user", "content": question}], output_format=Plan,
    )
    return response.parsed_output.steps, response.usage


def save_note(title, text):
    """Write a Markdown note, and add it to your notes so search_notes can find it later."""
    NOTES.mkdir(exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:50] or "note"
    path = NOTES / f"{date.today()}-{slug}.md"
    path.write_text(f"# {title}\n\n{text}\n", encoding="utf-8")
    index_file(path, NOTES)
    return {"saved": path.name}


def ask_to_approve(name, args):
    """Human approval: show what the agent wants to do and wait for a yes."""
    print(f"\n  The agent wants to run {name}:")
    for key, value in args.items():
        print(f"    {key}: {value}")
    return input("  Allow it? [y/N] ").strip().lower() == "y"


def run_tool(name, args, approve):
    """Run one tool call. Returns the text to send back, and whether it failed."""
    if name in ("search_wikipedia", "read_page"):
        return run_wiki_tool(name, args)  # E5's code, with its error handling
    if name in NEEDS_APPROVAL and not approve(name, args):
        return "The user said no. Don't try again; tell them it wasn't saved.", True
    if name == "search_notes":
        return json.dumps(search(args["query"]) or "No notes matched."), False
    if name == "save_note":
        return json.dumps(save_note(args["title"], args["text"])), False
    return f"There is no tool called {name}.", True


def add_usage(state, usage):
    state["calls"] += 1
    state["tokens_in"] += usage.input_tokens
    state["tokens_out"] += usage.output_tokens
    state["cost"] = (state["tokens_in"] * PRICE_IN + state["tokens_out"] * PRICE_OUT) / 1_000_000


def steps(question, memory, tools=ALL_TOOLS, approve=ask_to_approve):
    """Run the agent on one question, yielding an event for each thing it does:
    a plan, each tool call, and finally "done" with the answer and what it cost."""
    state = {"calls": 0, "tokens_in": 0, "tokens_out": 0, "cost": 0.0, "tools": []}  # this run's state
    plan, usage = make_plan(question, memory)
    add_usage(state, usage)
    yield {"type": "plan", "steps": plan}

    numbered = "\n".join(f"{n}. {step}" for n, step in enumerate(plan, 1))
    messages = memory + [{"role": "user", "content": f"{question}\n\n<plan>\n{numbered}\n</plan>"}]
    offered = [tool for tool in TOOLS if tool["name"] in tools]
    seen = set()  # tool calls already made, to catch a loop asking for the same thing
    while True:
        if state["calls"] >= MAX_CALLS or state["cost"] >= MAX_COST:  # stop conditions, before every call
            answer = f"Stopped: this question reached its limit of {MAX_CALLS} model calls or ${MAX_COST}."
            break
        response = client.messages.create(
            model=MODEL, max_tokens=4000, system=SYSTEM, tools=offered, messages=messages,
        )
        add_usage(state, response.usage)
        messages.append({"role": "assistant", "content": response.content})
        if response.stop_reason != "tool_use":  # the model answered
            answer = "".join(block.text for block in response.content if block.type == "text")
            if response.stop_reason != "end_turn":
                answer += f"\n(Stopped early: {response.stop_reason})"
            break

        results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            yield {"type": "tool", "name": block.name, "input": block.input}
            state["tools"].append(block.name)
            key = block.name + json.dumps(block.input, sort_keys=True)
            if block.name not in tools:  # only the tools offered for this run, whatever the model asks
                text, failed = f"There is no tool called {block.name}.", True
            elif key in seen:
                text, failed = "You already made this exact call. Use its result above.", True
            else:
                seen.add(key)
                text, failed = run_tool(block.name, block.input, approve)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": failed})
        messages.append({"role": "user", "content": results})
    yield {"type": "done", "answer": answer, **state}


def ask(question, memory):
    """Run the agent in the terminal, then remember the question and answer for follow-ups."""
    for event in steps(question, memory):
        if event["type"] == "plan":
            print("  plan: " + " | ".join(event["steps"]))
        elif event["type"] == "tool":
            print(f"  -> {event['name']}({json.dumps(event['input'])})")
        elif event["type"] == "done":
            print(f"  [{event['calls']} model calls, {event['tokens_in']} tokens in, "
                  f"{event['tokens_out']} out, ${event['cost']:.5f}]\n")
            print(event["answer"])
            memory.append({"role": "user", "content": question})  # memory keeps the answers, not the tool calls
            memory.append({"role": "assistant", "content": event["answer"]})


def main():
    memory = []  # earlier questions and answers in this session
    print("Ask a research question. Type quit to stop.")
    while True:
        question = input("\nYou: ").strip()
        if question.lower() in ("quit", "exit"):
            break
        if not question:
            continue
        try:
            ask(question, memory)
        except anthropic.APIConnectionError:
            print("Could not reach the API. Check your internet connection and try again.")
        except anthropic.APIStatusError as error:  # a bad key, no credit, overloaded: after the SDK's retries
            print(f"The API answered {error.status_code}: {error.message}")


if __name__ == "__main__":
    main()
