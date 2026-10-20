"""Wikipedia tools for the research workers: E5's two tools, unchanged except that the site's
address can be changed with WIKI_URL (tests and the page's examples use a stand-in)."""
import json
import os
from urllib.parse import quote

import httpx

WIKI = os.environ.get("WIKI_URL", "https://en.wikipedia.org")
HEADERS = {"User-Agent": "research-team/0.1 (you@example.com)"}  # your email, as in E2

TOOLS = [
    {
        "name": "search_wikipedia",
        "description": "Search English Wikipedia. Returns up to 5 page titles, each with a one-line description.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string", "description": "A few search words"}},
                         "required": ["query"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "read_page",
        "description": "Read the summary of one Wikipedia page. Use an exact title from search_wikipedia.",
        "input_schema": {"type": "object", "properties": {"title": {"type": "string", "description": "The exact page title"}},
                         "required": ["title"], "additionalProperties": False},
        "strict": True,
    },
]


def search_wikipedia(query):
    response = httpx.get(f"{WIKI}/w/rest.php/v1/search/page", params={"q": query, "limit": 5}, headers=HEADERS, timeout=10)
    response.raise_for_status()
    return [{"title": page["title"], "description": page.get("description") or ""} for page in response.json()["pages"]]


def read_page(title):
    response = httpx.get(f"{WIKI}/api/rest_v1/page/summary/" + quote(title.replace(" ", "_")), headers=HEADERS,
                         timeout=10, follow_redirects=True)
    response.raise_for_status()
    data = response.json()
    return {"title": data["title"], "summary": data["extract"], "url": data["content_urls"]["desktop"]["page"]}


def run_tool(name, args):
    """Run one tool call. Returns the result (a list or dict), or raises ValueError with a message for Claude."""
    try:
        if name == "search_wikipedia":
            return search_wikipedia(args["query"])
        if name == "read_page":
            return read_page(args["title"])
    except httpx.HTTPStatusError as error:
        raise ValueError(f"Wikipedia answered {error.response.status_code}. Check the title and try again.") from None
    except httpx.RequestError:
        raise ValueError("Could not reach Wikipedia.") from None
    raise ValueError(f"There is no tool called {name}.")


def as_text(result):
    return json.dumps(result, ensure_ascii=False)
