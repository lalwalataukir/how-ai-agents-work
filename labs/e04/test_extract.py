"""Offline tests for extract.py. The Claude client is faked, so no API key or network is needed."""
import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
import extract  # noqa: E402
from extract import Claim, Extract  # noqa: E402

ARTICLE = (HERE / "article.txt").read_text(encoding="utf-8")
GOOD = Extract(
    title="Riverside Library pilots an AI research helper",
    claims=[
        Claim(claim="The library started a six-month AI trial.", quote="has started a six-month trial of an AI assistant"),
        Claim(claim="It answered 4,200 questions in its first month.", quote="the assistant answered 4,200 questions"),
        # this quote crosses a line break in the file; spacing differences must not matter
        Claim(claim="Reviewers rated 81% of answers accurate.", quote="They rated 81% of the reviewed answers as accurate and complete"),
    ],
    sources=["Maria Okafor, head librarian", "Regional Libraries Council report"],
)
INVENTED = GOOD.model_copy(update={"claims": GOOD.claims[:2] + [Claim(claim="Visitors loved it.", quote="visitors loved the assistant")]})


class FakeMessages:
    def __init__(self, results):
        self.results, self.calls = list(results), []

    def parse(self, **kwargs):
        self.calls.append(dict(kwargs, messages=list(kwargs["messages"])))
        result, stop = self.results.pop(0)
        return NS(parsed_output=result, stop_reason=stop, content=[NS(type="text", text=result.model_dump_json() if result else "")])


class ExtractTest(unittest.TestCase):
    def run_extract(self, results, attempts=2):
        fake = FakeMessages(results)
        out = io.StringIO()
        with mock.patch.object(extract, "client", NS(messages=fake)), redirect_stdout(out):
            result = extract.extract(ARTICLE, attempts=attempts)
        return result, fake.calls, out.getvalue()

    def test_good_answer_passes_first_time(self):
        result, calls, out = self.run_extract([(GOOD, "end_turn")])
        self.assertEqual(result, GOOD)
        self.assertIs(calls[0]["output_format"], Extract)
        self.assertEqual(calls[0]["output_config"], {"effort": "low"})
        self.assertIn("<article>\nRiverside Library", calls[0]["messages"][0]["content"])
        self.assertIn("Checks passed on attempt 1.", out)

    def test_invented_quote_triggers_a_retry_with_the_problem_listed(self):
        result, calls, out = self.run_extract([(INVENTED, "end_turn"), (GOOD, "end_turn")])
        self.assertEqual(result, GOOD)
        retry = calls[1]["messages"]
        self.assertEqual([m["role"] for m in retry], ["user", "assistant", "user"])
        self.assertIn("'visitors loved the assistant'", retry[2]["content"])
        self.assertIn("Attempt 1: 1 problem(s). Asking again.", out)

    def test_gives_up_after_the_last_attempt(self):
        with self.assertRaises(ValueError) as caught:
            self.run_extract([(INVENTED, "end_turn"), (INVENTED, "end_turn")])
        self.assertIn("not in the article", str(caught.exception))

    def test_too_few_claims_is_a_problem(self):
        two = GOOD.model_copy(update={"claims": GOOD.claims[:2]})
        self.assertEqual(extract.check(two, ARTICLE), ["There are 2 claims. Give 3 to 5."])

    def test_stopping_early_is_an_error(self):
        with self.assertRaises(RuntimeError):
            self.run_extract([(None, "max_tokens")])

    def test_main_saves_the_json(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(extract, "client", NS(messages=FakeMessages([(GOOD, "end_turn")]))):
            cwd = os.getcwd()
            os.chdir(folder)
            try:
                with redirect_stdout(io.StringIO()):
                    extract.main(str(HERE / "article.txt"))
                saved = Extract.model_validate_json(Path("extract.json").read_text(encoding="utf-8"))
            finally:
                os.chdir(cwd)
        self.assertEqual(saved, GOOD)


if __name__ == "__main__":
    unittest.main()
