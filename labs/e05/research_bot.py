"""E5 lab: a research bot that searches Wikipedia with tools and cites what it read.

Run it with:
    uv run research_bot.py "Who coined the term artificial intelligence, and when?"
"""
import json
import sys
from urllib.parse import quote

import anthropic
import httpx
from dotenv import load_dotenv

load_dotenv()

MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10, 0.50  # dollars per million tokens, for this model
HEADERS = {"User-Agent": "research-assistant/0.1 (you@example.com)"}  # your email, as in E2
MAX_CALLS = 8  # a safety limit: at most this many model calls per question
SYSTEM = (
    "You are a research assistant. Use the tools to find facts on Wikipedia before you answer. "
    "Answer in at most 150 words. After each fact, cite the page it came from as [Page title]. "
    "If the pages you read don't answer the question, say so."
)

TOOLS = [
    {
        "name": "search_wikipedia",
        "description": "Search English Wikipedia. Returns up to 5 page titles, each with a one-line "
                       "description. Use it to decide which pages to read.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "A few search words"}},
            "required": ["query"],
            "additionalProperties": False,
        },
        "strict": True,  # the model's arguments always match this schema
    },
    {
        "name": "read_page",
        "description": "Read the summary of one Wikipedia page. Use an exact title from search_wikipedia.",
        "input_schema": {
            "type": "object",
            "properties": {"title": {"type": "string", "description": "The exact page title"}},
            "required": ["title"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]

client = anthropic.Anthropic()


def search_wikipedia(query):
    response = httpx.get("https://en.wikipedia.org/w/rest.php/v1/search/page",
                         params={"q": query, "limit": 5}, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return [{"title": page["title"], "description": page.get("description") or ""}
            for page in response.json()["pages"]]


def read_page(title):
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + quote(title.replace(" ", "_"))
    response = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
    response.raise_for_status()
    data = response.json()
    return {"title": data["title"], "summary": data["extract"], "url": data["content_urls"]["desktop"]["page"]}


def run_tool(name, args):
    """Run one tool call. Returns the text to send back, and whether it failed."""
    try:
        if name == "search_wikipedia":
            result = search_wikipedia(args["query"])
        elif name == "read_page":
            result = read_page(args["title"])
        else:
            return f"There is no tool called {name}.", True
    except httpx.HTTPStatusError as error:
        return f"Wikipedia answered {error.response.status_code}. Check the title and try again.", True
    except httpx.RequestError:
        return "Could not reach Wikipedia.", True
    return json.dumps(result), False


def research(question):
    """The tool-use loop: call the model, run the tools it asks for, send back the results, repeat."""
    messages = [{"role": "user", "content": question}]
    tokens_in = tokens_out = 0
    for call in range(1, MAX_CALLS + 1):
        response = client.messages.create(
            model=MODEL, max_tokens=4000, system=SYSTEM, tools=TOOLS, messages=messages,
        )
        tokens_in += response.usage.input_tokens
        tokens_out += response.usage.output_tokens
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":  # no more tools wanted: this is the answer
            cost = (tokens_in * PRICE_IN + tokens_out * PRICE_OUT) / 1_000_000
            print(f"  [{call} model calls, {tokens_in} tokens in, {tokens_out} out, ${cost:.5f}]\n")
            answer = "".join(block.text for block in response.content if block.type == "text")
            if response.stop_reason != "end_turn":
                answer += f"\n(Stopped early: {response.stop_reason})"
            return answer

        results = []  # one tool_result for every tool_use, all sent back in one message
        for block in response.content:
            if block.type == "tool_use":
                print(f"  -> {block.name}({json.dumps(block.input)})")
                text, failed = run_tool(block.name, block.input)
                results.append({"type": "tool_result", "tool_use_id": block.id, "content": text, "is_error": failed})
        messages.append({"role": "user", "content": results})
    return f"Stopped after {MAX_CALLS} model calls without a final answer."


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or input("Question: ")
    print(research(question))
