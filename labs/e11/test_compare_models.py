"""Offline tests for the E11 lab: compare_models.py and local_rag.py.
The agent, the judge, Claude and Ollama are all faked, so no API key, network or Ollama is needed."""
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
os.environ.setdefault("LANGFUSE_TRACING_ENABLED", "false")  # no traces from these tests
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-lf-test")
import anthropic  # noqa: E402
import chromadb  # noqa: E402
import httpx2  # noqa: E402

LABS = Path(__file__).parent.parent
for folder in ("e05", "e06", "e08", "e10", "e11"):  # in your repo these files sit side by side
    sys.path.insert(0, str(LABS / folder))
for name in ("agent", "guard", "run_evals", "compare_models", "local_rag"):  # other labs have their own agent.py
    sys.modules.pop(name, None)
with mock.patch.object(chromadb, "PersistentClient", lambda path: chromadb.EphemeralClient()):
    import agent  # noqa: E402  (E10's hardened agent: the latest one)
    import compare_models  # noqa: E402
    import local_rag  # noqa: E402
import run_evals  # noqa: E402

CASES = json.loads(run_evals.CASES.read_text(encoding="utf-8"))
TOKENS = {"tokens_in": 210, "cache_written": 1150, "cache_read": 3850, "tokens_out": 301}


def fake_steps(answers, seen):
    """Answers by model: each model gets the case right or wrong as scripted."""
    def steps(question, memory, approve):
        assert approve("save_note", {}) is False
        seen.append(agent.MODEL)
        yield {"type": "done", "answer": answers[agent.MODEL](question), "calls": 4, "cost": 0.0, **TOKENS}
    return steps


def good(question):
    case = next(c for c in CASES if c["question"] == question)
    return " ".join(w.split("|")[0] for w in case["must_include"]) + " [Source]"


class FakeJudge:
    def __init__(self):
        self.calls = 0

    def parse(self, **kwargs):
        self.calls += 1
        return NS(parsed_output=run_evals.Verdict(reason="Fine.", passed=True), usage=NS(input_tokens=600, output_tokens=40))


class CompareTest(unittest.TestCase):
    def setUp(self):
        self.report = Path(tempfile.mkdtemp()) / "model_report.json"
        for patch in (mock.patch.object(compare_models, "REPORT", self.report),
                      mock.patch.object(agent, "MODEL", agent.MODEL),
                      mock.patch.object(agent, "PRICE_IN", agent.PRICE_IN), mock.patch.object(agent, "PRICE_OUT", agent.PRICE_OUT)):
            patch.start()
            self.addCleanup(patch.stop)

    def test_cost_uses_each_models_own_prices_including_the_cache(self):
        self.assertAlmostEqual(compare_models.cost_of("claude-haiku-5-5", TOKENS), 0.00035375)
        self.assertAlmostEqual(compare_models.cost_of("claude-sonnet-5-5", TOKENS), 0.007075)
        self.assertAlmostEqual(compare_models.cost_of("claude-opus-5-5", TOKENS), 0.01338)

    def test_runs_every_case_on_every_model_and_picks_the_cheapest_good_enough(self):
        seen, judge = [], FakeJudge()
        answers = {"claude-haiku-5-5": lambda q: good(q) if q != CASES[1]["question"] else "Somewhere [x].",
                   "claude-sonnet-5-5": good, "claude-opus-5-5": good}
        out = io.StringIO()
        with mock.patch.object(agent, "steps", fake_steps(answers, seen)), \
             mock.patch.object(agent, "client", NS(messages=judge)), redirect_stdout(out):
            best = compare_models.main(4)
        self.assertEqual(seen, ["claude-haiku-5-5"] * 4 + ["claude-sonnet-5-5"] * 4 + ["claude-opus-5-5"] * 4)
        self.assertEqual(judge.calls, 11)  # the failed code check skips the judge once
        report = json.loads(self.report.read_text())
        self.assertEqual([m["score"] for m in report["models"]], [0.75, 1.0, 1.0])
        self.assertEqual([m["per_1000"] for m in report["models"]], [0.354, 7.075, 13.38])
        self.assertEqual(best["model"], "claude-sonnet-5-5")  # Haiku's 75% is under the 85% minimum
        text = out.getvalue()
        self.assertIn("  claude-haiku-5-5   dartmouth-place  FAIL", text)
        self.assertIn("claude-opus-5-5      100%              $13.380", text)
        self.assertIn("Cheapest model at or above 85%: claude-sonnet-5-5", text)

    def test_the_agent_is_switched_to_each_model_and_its_prices(self):
        prices = []

        def steps(question, memory, approve):
            prices.append((agent.MODEL, agent.PRICE_IN, agent.PRICE_OUT))
            yield {"type": "done", "answer": good(question), "calls": 4, "cost": 0.0, **TOKENS}

        with mock.patch.object(agent, "steps", steps), mock.patch.object(agent, "client", NS(messages=FakeJudge())), \
             redirect_stdout(io.StringIO()):
            best = compare_models.main(1)
        self.assertEqual(prices, [("claude-haiku-5-5", 0.10, 0.50), ("claude-sonnet-5-5", 2.00, 10.00), ("claude-opus-5-5", 4.00, 20.00)])
        self.assertEqual(best["model"], "claude-haiku-5-5")

    def test_an_api_error_fails_that_case_only(self):
        def steps(question, memory, approve):
            if agent.MODEL == "claude-opus-5-5":
                raise anthropic.APIConnectionError(request=httpx2.Request("POST", "https://api.anthropic.com/v1/messages"))
            yield {"type": "done", "answer": good(question), "calls": 4, "cost": 0.0, **TOKENS}

        with mock.patch.object(agent, "steps", steps), mock.patch.object(agent, "client", NS(messages=FakeJudge())), \
             redirect_stdout(io.StringIO()):
            compare_models.main(2)
        opus = json.loads(self.report.read_text())["models"][2]
        self.assertEqual((opus["score"], opus["per_1000"]), (0.0, None))


class LocalTest(unittest.TestCase):
    HITS = [{"source": "library-handbook.md", "page": 1, "text": "Adult items cost 20 cents a day.", "distance": 0.25}]

    def test_the_local_model_gets_the_same_prompt_through_ollama(self):
        self.assertEqual(str(local_rag.local.base_url).rstrip("/"), "http://localhost:11434")
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return NS(content=[NS(type="thinking", thinking="..."), NS(type="text", text="20 cents a day [library-handbook.md, page 1].")])

        with mock.patch.object(local_rag, "local", NS(messages=NS(create=create))):
            text = local_rag.answer_locally("Late fee?", self.HITS)
        self.assertEqual(text, "20 cents a day [library-handbook.md, page 1].")
        self.assertEqual(calls[0]["model"], "qwen3:8b")
        self.assertEqual(calls[0]["system"], local_rag.rag.SYSTEM)
        self.assertIn('<source file="library-handbook.md" page="1">', calls[0]["messages"][0]["content"])
        self.assertNotIn("output_config", calls[0])  # only the basics, which Ollama supports

    def test_compare_prints_both_answers_and_explains_a_missing_ollama(self):
        def refused(**kwargs):
            raise anthropic.APIConnectionError(request=httpx2.Request("POST", "http://localhost:11434/v1/messages"))

        out = io.StringIO()
        with mock.patch.object(local_rag.rag, "search", return_value=self.HITS), \
             mock.patch.object(local_rag.rag, "answer", return_value="20 cents a day."), \
             mock.patch.object(local_rag, "local", NS(messages=NS(create=refused))), redirect_stdout(out):
            local_rag.compare("Late fee?")
        text = out.getvalue()
        self.assertIn("--- Claude Haiku 5.5 (", text)
        self.assertIn("20 cents a day.", text)
        self.assertIn("--- qwen3:8b, on this computer (", text)
        self.assertIn("Could not reach Ollama. Is it running?", text)

    def test_nothing_found_means_no_model_calls(self):
        out = io.StringIO()
        with mock.patch.object(local_rag.rag, "search", return_value=[]), \
             mock.patch.object(local_rag.rag, "answer") as answer, redirect_stdout(out):
            local_rag.compare("Capital of France?")
        answer.assert_not_called()
        self.assertEqual(out.getvalue(), "Nothing close enough in your notes.\n")


if __name__ == "__main__":
    unittest.main()
