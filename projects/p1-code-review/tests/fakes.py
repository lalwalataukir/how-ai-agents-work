"""A fake Claude for the tests. It answers with what each test scripts, and records every request,
so the tests need no API key or internet connection."""
from types import SimpleNamespace as NS

from anthropic.types import TextBlock, ToolUseBlock


def answer(review):
    """A reply that ends the turn with a review."""
    text = TextBlock(type="text", text=review.model_dump_json(), citations=None)
    return NS(content=[text], stop_reason="end_turn", parsed_output=review,
              usage=NS(input_tokens=2000, output_tokens=400))


def reads(*calls):
    """A reply that asks for read_file calls, each given as (path, start, end)."""
    blocks = [ToolUseBlock(type="tool_use", id=f"toolu_{i}", name="read_file",
                           input={"path": path, "start": start, "end": end})
              for i, (path, start, end) in enumerate(calls, 1)]
    return NS(content=blocks, stop_reason="tool_use", parsed_output=None,
              usage=NS(input_tokens=1500, output_tokens=100))


class FakeClaude:
    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []
        self.messages = self  # so the code can call client.messages.parse(...)

    def parse(self, **request):
        self.requests.append(dict(request, messages=list(request["messages"])))
        return self.replies.pop(0)
