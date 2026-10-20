"""E7 lab, part 2: the same agent as a LangGraph graph. LangGraph saves the state after every
step, so the graph can pause for your approval and pick up where it left off.

Run it with:
    uv run agent_graph.py          # chat with it
    uv run agent_graph.py --draw   # print the graph as a Mermaid diagram
"""
import json
import operator
import sys
from typing import Annotated, TypedDict

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

import agent  # the model, prompts, tools and limits from agent.py


class State(TypedDict):
    messages: Annotated[list, operator.add]  # each step's new messages are added to the list
    calls: int      # model calls for the current question
    cost: float     # dollars for the current question
    approved: dict  # tool_use id -> the person's yes or no


def call_cost(usage):
    return (usage.input_tokens * agent.PRICE_IN + usage.output_tokens * agent.PRICE_OUT) / 1_000_000


def plan(state):
    """Make a plan for the newest question, and reset the per-question limits."""
    steps, usage = agent.make_plan(state["messages"][-1]["content"], [])
    print("  plan: " + " | ".join(steps))
    numbered = "\n".join(f"{n}. {step}" for n, step in enumerate(steps, 1))
    return {"messages": [{"role": "user", "content": f"<plan>\n{numbered}\n</plan>"}],
            "calls": 1, "cost": call_cost(usage), "approved": {}}


def model(state):
    """Call Claude, unless this question has used its limits."""
    if state["calls"] >= agent.MAX_CALLS or state["cost"] >= agent.MAX_COST:
        text = f"Stopped: this question reached its limit of {agent.MAX_CALLS} model calls or ${agent.MAX_COST}."
        return {"messages": [{"role": "assistant", "content": [{"type": "text", "text": text}]}]}
    response = agent.client.messages.create(
        model=agent.MODEL, max_tokens=4000, system=agent.SYSTEM, tools=agent.TOOLS, messages=state["messages"],
    )
    content = [block.to_dict() for block in response.content]  # plain data, so the checkpoint can save it
    return {"messages": [{"role": "assistant", "content": content}],
            "calls": state["calls"] + 1, "cost": state["cost"] + call_cost(response.usage)}


def approve(state):
    """Pause the graph for a yes or no on every call that changes something."""
    decisions = {}
    for block in state["messages"][-1]["content"]:
        if block["type"] == "tool_use" and block["name"] in agent.NEEDS_APPROVAL:
            decisions[block["id"]] = interrupt({"tool": block["name"], "input": block["input"]})
    return {"approved": decisions}


def tools(state):
    """Run every tool the model asked for and send all the results back together."""
    results = []
    for block in state["messages"][-1]["content"]:
        if block["type"] == "tool_use":
            print(f"  -> {block['name']}({json.dumps(block['input'])})")
            decision = state["approved"].get(block["id"], False)
            text, failed = agent.run_tool(block["name"], block["input"], lambda name, args: decision)
            results.append({"type": "tool_result", "tool_use_id": block["id"], "content": text, "is_error": failed})
    return {"messages": [{"role": "user", "content": results}]}


def next_step(state):
    """After the model: run tools if it asked for any, otherwise finish."""
    asked = any(block["type"] == "tool_use" for block in state["messages"][-1]["content"])
    return "approve" if asked else END


builder = StateGraph(State)
builder.add_node("plan", plan)
builder.add_node("model", model)
builder.add_node("approve", approve)
builder.add_node("tools", tools)
builder.add_edge(START, "plan")
builder.add_edge("plan", "model")
builder.add_conditional_edges("model", next_step, ["approve", END])
builder.add_edge("approve", "tools")
builder.add_edge("tools", "model")
graph = builder.compile(checkpointer=InMemorySaver())  # saves the state after every step


def ask(question, config):
    result = graph.invoke({"messages": [{"role": "user", "content": question}]}, config)
    while "__interrupt__" in result:  # the graph paused for approval: ask, then resume it
        request = result["__interrupt__"][0].value
        yes = agent.ask_to_approve(request["tool"], request["input"])
        result = graph.invoke(Command(resume=yes), config)
    answer = "".join(block["text"] for block in result["messages"][-1]["content"] if block["type"] == "text")
    print(f"  [{result['calls']} model calls, ${result['cost']:.5f}]\n")
    print(answer)
    return answer


def main():
    config = {"configurable": {"thread_id": "terminal"}}  # one conversation, remembered by the checkpointer
    print("Ask a research question. Type quit to stop.")
    while True:
        question = input("\nYou: ").strip()
        if question.lower() in ("quit", "exit"):
            break
        if question:
            ask(question, config)


if __name__ == "__main__":
    if sys.argv[1:] == ["--draw"]:
        print(graph.get_graph().draw_mermaid())
    else:
        main()
