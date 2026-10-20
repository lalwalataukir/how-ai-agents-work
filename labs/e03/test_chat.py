"""Offline tests for chat.py. The Claude client is faked, so no API key or network is needed."""
import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never sent anywhere: the client is faked
import anthropic  # noqa: E402
import httpx2  # noqa: E402  (the HTTP library the anthropic SDK uses)

sys.path.insert(0, str(Path(__file__).parent))
import chat  # noqa: E402

REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


class FakeStream:
    def __init__(self, text, tokens_in, tokens_out, stop="end_turn"):
        self.text, self.stop = text, stop
        self.usage = NS(input_tokens=tokens_in, output_tokens=tokens_out)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    @property
    def text_stream(self):
        return iter(self.text.split(" ")[:1] + [" " + w for w in self.text.split(" ")[1:]])

    def get_final_message(self):
        return NS(content=[NS(type="thinking", thinking=""), NS(type="text", text=self.text)],
                  usage=self.usage, stop_reason=self.stop)


class FakeMessages:
    def __init__(self, outcomes):
        self.outcomes, self.calls = list(outcomes), []

    def stream(self, **kwargs):
        self.calls.append(dict(kwargs, messages=list(kwargs["messages"])))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class ChatTest(unittest.TestCase):
    def run_chat(self, inputs, outcomes):
        fake = FakeMessages(outcomes)
        out = io.StringIO()
        with mock.patch.object(chat, "client", NS(messages=fake)), \
             mock.patch("builtins.input", side_effect=inputs), redirect_stdout(out):
            chat.main()
        return fake.calls, out.getvalue()

    def test_remembers_the_conversation_and_adds_up_cost(self):
        calls, out = self.run_chat(
            ["What is RAG?", "Give one example.", "quit"],
            [FakeStream("RAG looks things up first.", 41, 96), FakeStream("A support bot.", 150, 80)])
        self.assertEqual(calls[0]["model"], "claude-haiku-5-5")
        self.assertEqual(calls[0]["output_config"], {"effort": "low"})
        self.assertIn("research assistant", calls[0]["system"])
        second = calls[1]["messages"]
        self.assertEqual([m["role"] for m in second], ["user", "assistant", "user"])
        self.assertEqual(second[1]["content"][1].text, "RAG looks things up first.")  # the whole reply was kept
        self.assertIn("Claude: RAG looks things up first.", out)
        self.assertIn("[41 tokens in, 96 out, $0.00005 this turn, $0.00005 so far]", out)
        self.assertIn("Session cost: $0.00011", out)

    def test_connection_error_forgets_the_unanswered_question(self):
        calls, out = self.run_chat(
            ["First try", "Second try", "quit"],
            [anthropic.APIConnectionError(request=REQUEST), FakeStream("Hello.", 30, 10)])
        self.assertIn("Could not reach the API", out)
        self.assertEqual([m["content"] for m in calls[1]["messages"]], ["Second try"])

    def test_rate_limit_is_reported_and_the_chat_goes_on(self):
        error = anthropic.RateLimitError("slow down", response=httpx2.Response(429, request=REQUEST), body=None)
        calls, out = self.run_chat(["Hi", "Hi again", "quit"], [error, FakeStream("Hello.", 30, 10)])
        self.assertIn("The API answered 429", out)
        self.assertEqual(len(calls), 2)

    def test_bad_key_stops_the_chat(self):
        error = anthropic.AuthenticationError("bad key", response=httpx2.Response(401, request=REQUEST), body=None)
        calls, out = self.run_chat(["Hi"], [error])
        self.assertIn("The API key was rejected", out)
        self.assertIn("Session cost: $0.00000", out)

    def test_cut_off_reply_is_flagged(self):
        _, out = self.run_chat(["Tell me everything", "quit"], [FakeStream("Well...", 20, 2000, stop="max_tokens")])
        self.assertIn("The reply was cut off", out)


if __name__ == "__main__":
    unittest.main()
