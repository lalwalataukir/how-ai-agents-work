"""Measure search: for each question, is a right chunk in the top 5? That's recall@5.
No model calls, so it's free: run it after every change to chunking or search.

Run it with:
    uv run eval_search.py
"""
import json
from pathlib import Path

import qa

CASES = json.loads((Path(__file__).parent / "search_questions.json").read_text(encoding="utf-8"))


def recall(index, mode, k=qa.TOP_K):
    """The share of questions with a right chunk in the top k, and the questions that missed."""
    misses = []
    for case in CASES:
        found = {f"{c.path}::{c.name}" for c in index.search(case["question"], k, mode)}
        if not found & set(case["expect"]):
            misses.append(case["question"])
    return 1 - len(misses) / len(CASES), misses


def main():
    index = qa.Index(qa.ROOT)
    print(f"{len(CASES)} questions, {len(index.chunks)} chunks. Recall@{qa.TOP_K}:")
    for mode in ("keyword", "vector", "hybrid"):
        score, misses = recall(index, mode)
        print(f"  {mode:<8} {score:>4.0%}" + (f"   missed: {'; '.join(misses)}" if misses else ""))


if __name__ == "__main__":
    main()
