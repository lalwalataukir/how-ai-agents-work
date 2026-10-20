"""Fakes for the tests: a fake Claude that plays every role, and a fake Wikipedia, so the tests need
no API key or internet. The fake answers by role, not in a fixed order, because workers run in parallel."""
import os
import threading
import time
from types import SimpleNamespace as NS

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: Claude is faked
os.environ.setdefault("LANGFUSE_TRACING_ENABLED", "false")  # no traces from tests

from anthropic.types import TextBlock, ToolUseBlock  # noqa: E402

import team  # noqa: E402

QUESTIONS = ["What was the Dartmouth workshop?", "Who organised the Dartmouth workshop?", "What did the Dartmouth workshop lead to?"]
PAGES = {
    "What was the Dartmouth workshop?": "Dartmouth workshop",
    "Who organised the Dartmouth workshop?": "John McCarthy",
    "What did the Dartmouth workshop lead to?": "History of artificial intelligence",
}
SUMMARIES = {
    "Dartmouth workshop": "The Dartmouth workshop of 1956 is widely considered the founding event of AI as a field.",
    "John McCarthy": "John McCarthy coined the term artificial intelligence and organised the 1956 Dartmouth workshop with Marvin Minsky.",
    "History of artificial intelligence": "After 1956, AI research grew quickly, with labs at MIT, Stanford and Carnegie Mellon.",
}
GOOD = ("# The Dartmouth workshop\n\nThe 1956 Dartmouth workshop founded AI as a field [1].\n\n"
        "John McCarthy organised it with Marvin Minsky [2].\n\nAI research then grew at MIT and Stanford [3].")
BAD = GOOD.replace(" [2].", ".") + " [7]"


def usage(i=1000, o=100):
    return NS(input_tokens=i, output_tokens=o)


def search_wikipedia(query):
    return [{"title": PAGES.get(query, "Dartmouth workshop"), "description": "a page"}]


def read_page(title):
    return {"title": title, "summary": SUMMARIES.get(title, "No such page."),
            "url": "https://en.wikipedia.org/wiki/" + title.replace(" ", "_")}


class FakeClaude:
    """Plays every role. plan: the planner's questions. drafts: what the writer returns, in turn.
    critiques: (approved, issues) for each critique, in turn. tools_forever: workers never stop.
    delay: seconds each worker call takes. crash: a question whose worker call raises."""

    def __init__(self, plan=QUESTIONS, drafts=(GOOD,), critiques=((True, []),), tools_forever=False, delay=0.0, crash=None):
        self.plan, self.drafts, self.critiques = list(plan), list(drafts), list(critiques)
        self.tools_forever, self.delay, self.crash = tools_forever, delay, crash
        self.requests, self.lock = [], threading.Lock()
        self.messages = self  # so the code can call client.messages.create(...) and .parse(...)

    def record(self, request):
        with self.lock:
            self.requests.append(dict(request, messages=list(request["messages"])))

    def by(self, system):
        return [r for r in self.requests if r.get("system") == system]

    def parse(self, **request):
        self.record(request)
        if request.get("system") == team.PLANNER:
            return NS(parsed_output=team.Plan(questions=self.plan), usage=usage(300, 80))
        if request.get("system") == team.CRITIC:
            approved, issues = self.critiques.pop(0) if len(self.critiques) > 1 else self.critiques[0]
            return NS(parsed_output=team.Critique(issues=issues, approved=approved), usage=usage(2000, 150))
        verdict = request["output_format"](reason="Every claim is in the findings.", passed=True)  # the eval's judge
        return NS(parsed_output=verdict, usage=usage(1500, 40))

    def create(self, **request):
        self.record(request)
        if request["system"] == team.WRITER:
            text = self.drafts.pop(0) if len(self.drafts) > 1 else self.drafts[0]
            return NS(content=[TextBlock(type="text", text=text, citations=None)], stop_reason="end_turn", usage=usage(2500, 400))
        time.sleep(self.delay)
        question = request["messages"][0]["content"]
        if question == self.crash:
            raise RuntimeError("the model is overloaded")
        step = sum(1 for m in request["messages"] if m["role"] == "user") - 1
        title = PAGES.get(question, "Dartmouth workshop")
        if self.tools_forever or step < 2:
            name, args = ("search_wikipedia", {"query": question}) if step % 2 == 0 else ("read_page", {"title": title})
            block = ToolUseBlock(type="tool_use", id=f"toolu_{step}", name=name, input=args)
            return NS(content=[block], stop_reason="tool_use", usage=usage())
        text = f"{SUMMARIES[title]} [{title}]"
        return NS(content=[TextBlock(type="text", text=text, citations=None)], stop_reason="end_turn", usage=usage())
