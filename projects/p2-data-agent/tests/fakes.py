"""A fake Claude and a test database. The fake answers with what each test scripts, and records
every request, so the tests need no API key or internet connection."""
import tempfile
from functools import cache
from pathlib import Path
from types import SimpleNamespace as NS

from anthropic.types import TextBlock, ToolUseBlock

import make_data


@cache
def test_db():
    """A fresh shop.db in a temporary folder, made once per test run."""
    path = Path(tempfile.mkdtemp()) / "shop.db"
    make_data.build(path)
    return path


def answer(text, value):
    """A reply that ends the turn with an Answer."""
    from analyst import Answer
    parsed = Answer(answer=text, value=value)
    return NS(content=[TextBlock(type="text", text=parsed.model_dump_json(), citations=None)],
              stop_reason="end_turn", parsed_output=parsed, usage=NS(input_tokens=1200, output_tokens=80))


def calls(*tools):
    """A reply that asks for tool calls, each given as (name, input)."""
    blocks = [ToolUseBlock(type="tool_use", id=f"toolu_{i}", name=name, input=args)
              for i, (name, args) in enumerate(tools, 1)]
    return NS(content=blocks, stop_reason="tool_use", parsed_output=None, usage=NS(input_tokens=1000, output_tokens=60))


def sql(query):
    return ("run_sql", {"sql": query})


class FakeClaude:
    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []
        self.messages = self  # so the code can call client.messages.parse(...)

    def parse(self, **request):
        self.requests.append(dict(request, messages=list(request["messages"])))
        return self.replies.pop(0)
