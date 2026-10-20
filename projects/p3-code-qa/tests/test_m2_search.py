"""Milestone 2: keyword and vector search"""
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: no test calls Claude
sys.path.insert(0, str(Path(__file__).parent.parent))
import qa  # noqa: E402
from fakes import TINYSHOP, fake_collection  # noqa: E402

HINT = ("words: re.findall the identifiers, split each at _ and at a lower-to-upper case change, lower-case and stem() "
        "every part, and drop STOP words. BM25 adds, for each question word in a chunk, idf x tf x (k1 + 1) / (tf + k1 x "
        "(1 - b + b x length / average)). fuse adds 1 / (60 + rank) per list and sorts by the total.")
CASES = json.loads((Path(__file__).parent.parent / "search_questions.json").read_text(encoding="utf-8"))
Chunk = qa.Chunk


class WordsTest(unittest.TestCase):
    def test_identifiers_are_split_lowered_and_stemmed(self):
        self.assertEqual(sorted(qa.words("apply_coupon")), ["apply", "apply_coupon", "coupon"])
        self.assertEqual(sorted(qa.words("applyCoupon")), ["apply", "applycoupon", "coupon"])
        self.assertEqual(qa.words("hashed passwords"), ["hash", "password"])

    def test_common_words_are_dropped(self):
        self.assertEqual(qa.words("Where is the cart?"), ["cart"])


class KeywordTest(unittest.TestCase):
    def setUp(self):
        self.chunks = [Chunk("a.py", "tax_for", 1, 3, "def tax_for(region):\n    return rate(region)"),
                       Chunk("b.py", "ship", 1, 2, "def ship(region, weight):\n    return weight"),
                       Chunk("c.py", "hello", 1, 1, "print('hello')")]
        self.index = qa.Keyword(self.chunks)

    def test_rare_words_count_most(self):
        self.assertEqual([c.name for c in self.index.search("tax for this region")], ["tax_for", "ship"])
        self.assertEqual([c.name for c in self.index.search("weight")], ["ship"])

    def test_no_matching_word_no_result(self):
        self.assertEqual(self.index.search("database"), [])

    def test_at_most_k_results(self):
        self.assertEqual(len(self.index.search("region", k=1)), 1)

    def test_on_tinyshop_identifiers_come_first(self):
        index = qa.Keyword(qa.chunk_repo(TINYSHOP))
        self.assertEqual(index.search("What does discount_for do?")[0].ref, "tinyshop/coupons.py:11-17")
        self.assertEqual(index.search("Where are passwords hashed?")[0].name, "hash_password")


class FuseTest(unittest.TestCase):
    def test_reciprocal_rank_fusion(self):
        a, b, c, d = (Chunk("x.py", n, i, i, "") for i, n in enumerate("abcd", 1))
        self.assertEqual([x.name for x in qa.fuse([a, b, c], [c, d, a], k=4)], ["a", "c", "b", "d"])

    def test_a_chunk_in_both_lists_beats_one_at_the_top_of_one(self):
        a, b, c = (Chunk("x.py", n, i, i, "") for i, n in enumerate("abc", 1))
        self.assertEqual(qa.fuse([a, b], [c, b])[0].name, "b")


class IndexTest(unittest.TestCase):
    def setUp(self):
        patch = mock.patch.object(qa, "collection", fake_collection)
        patch.start()
        self.addCleanup(patch.stop)
        self.index = qa.Index(TINYSHOP)

    def test_every_mode_returns_k_chunks(self):
        for mode in ("keyword", "vector", "hybrid"):
            found = self.index.search("refund an order", mode=mode)
            self.assertEqual(len(found), qa.TOP_K, mode)
            self.assertTrue(all(isinstance(c, Chunk) for c in found))

    def test_keyword_recall_on_the_eval_questions(self):
        hits = sum(bool({f"{c.path}::{c.name}" for c in self.index.search(case["question"], mode="keyword")} & set(case["expect"]))
                   for case in CASES)
        self.assertGreaterEqual(hits, 16)  # 80% of 20


if __name__ == "__main__":
    unittest.main()
