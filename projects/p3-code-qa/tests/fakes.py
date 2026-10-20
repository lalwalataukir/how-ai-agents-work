"""Fakes for the tests: a fake Claude, a tiny stand-in embedding so Chroma needs no model download,
and a copy of tinyshop with some files an attacker would want. No API key or internet needed."""
import hashlib
import math
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from types import SimpleNamespace as NS

import chromadb
from anthropic.types import TextBlock, ToolUseBlock
from chromadb.api.types import EmbeddingFunction

HERE = Path(__file__).parent.parent
TINYSHOP = HERE / "tinyshop"


class WordHash(EmbeddingFunction):
    """A stand-in embedding: each word adds 1 to one of 256 slots. Enough to test the plumbing."""

    def __init__(self):
        pass

    def __call__(self, input):
        vectors = []
        for text in input:
            vector = [0.0] * 256
            for word in re.findall(r"[a-z]+", text.lower()):
                vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % 256] += 1
            norm = math.sqrt(sum(x * x for x in vector)) or 1.0
            vectors.append([x / norm for x in vector])
        return vectors


def fake_collection():
    """An in-memory Chroma collection with the stand-in embedding, new each time."""
    return chromadb.EphemeralClient().create_collection(
        "code-" + uuid.uuid4().hex[:8], embedding_function=WordHash(), configuration={"hnsw": {"space": "cosine"}})


def repo():
    """A fresh copy of tinyshop in a temporary folder, plus a .env, a .git folder and a key file."""
    root = Path(tempfile.mkdtemp()) / "tinyshop"
    shutil.copytree(TINYSHOP, root)
    (root / ".env").write_text("TINYSHOP_SECRET_KEY=test-secret\n", encoding="utf-8")
    (root / ".git").mkdir()
    (root / ".git" / "config").write_text("[remote]\n", encoding="utf-8")
    (root / "deploy_key.pem").write_text("-----BEGIN KEY-----\n", encoding="utf-8")
    (root.parent / "outside.txt").write_text("not part of the repo\n", encoding="utf-8")
    return root


def text(t):
    return TextBlock(type="text", text=t, citations=None)


def use(i, name, args):
    return ToolUseBlock(type="tool_use", id=f"toolu_{i}", name=name, input=args)


def reply(*blocks):
    stop = "tool_use" if any(b.type == "tool_use" for b in blocks) else "end_turn"
    return NS(content=list(blocks), stop_reason=stop, usage=NS(input_tokens=1500, output_tokens=120))


class FakeClaude:
    def __init__(self, *replies):
        self.replies, self.requests = list(replies), []
        self.messages = self  # so the code can call client.messages.create(...)

    def create(self, **request):
        self.requests.append(dict(request, messages=list(request["messages"])))
        return self.replies.pop(0)
