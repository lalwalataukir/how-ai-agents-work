"""E11 lab: answer from your notes with a model running on your own computer, through Ollama,
and compare it with Claude on the same question.

First install Ollama from ollama.com and download a model:
    ollama pull qwen3:8b
Then run:
    uv run local_rag.py "How much will I pay if I bring a book back late?"
"""
import sys
import time

import anthropic

import rag  # E6: search your notes, and answer with Claude

LOCAL_MODEL = "qwen3:8b"  # any model you've pulled with Ollama
# Ollama understands the same Messages API, so the same SDK works: only the address changes.
local = anthropic.Anthropic(base_url="http://localhost:11434", api_key="ollama")  # Ollama ignores the key


def answer_locally(question, hits):
    """The same prompt as rag.answer, sent to the local model. No data leaves your computer."""
    sources = "\n".join(
        f'<source file="{hit["source"]}" page="{hit["page"]}">\n{hit["text"]}\n</source>' for hit in hits
    )
    response = local.messages.create(
        model=LOCAL_MODEL, max_tokens=2000, system=rag.SYSTEM,
        messages=[{"role": "user", "content": f"<sources>\n{sources}\n</sources>\n\nQuestion: {question}"}],
    )
    return "".join(block.text for block in response.content if block.type == "text")


def compare(question):
    hits = rag.search(question)
    if not hits:
        print("Nothing close enough in your notes.")
        return
    for name, ask in (("Claude Haiku 5.5", lambda: rag.answer(question, hits)),
                      (f"{LOCAL_MODEL}, on this computer", lambda: answer_locally(question, hits))):
        start = time.perf_counter()
        try:
            text = ask()
        except anthropic.APIConnectionError:
            text = "Could not reach Ollama. Is it running? Start the Ollama app, or run `ollama serve`."
        print(f"--- {name} ({time.perf_counter() - start:.1f} s)\n{text}\n")


if __name__ == "__main__":
    compare(" ".join(sys.argv[1:]) or input("Question: "))
