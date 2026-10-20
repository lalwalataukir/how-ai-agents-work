"""Offline tests for rag.py. Chroma runs in memory with a tiny word-count embedding instead of its
downloaded model, and the Claude client is faked, so no API key, download or network is needed."""
import io
import math
import os
import re
import sys
import tempfile
import unittest
import uuid
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace as NS
from unittest import mock

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")
import chromadb  # noqa: E402
from chromadb.api.types import EmbeddingFunction  # noqa: E402

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
with mock.patch.object(chromadb, "PersistentClient", lambda path: chromadb.EphemeralClient()):
    import rag  # noqa: E402  (in memory: the test leaves no chroma folder behind)

WORDS = ["late", "charge", "cents", "lose", "owe", "borrow", "phone", "libby", "sunday", "open", "wifi", "print", "found"]


class WordCounts(EmbeddingFunction):
    """A stand-in embedding: how often each of a few words appears. Enough to test the plumbing."""

    def __init__(self):
        pass

    def __call__(self, input):
        vectors = []
        for text in input:
            words = re.findall(r"[a-z]+", text.lower())
            vector = [float(sum(w.startswith(key) for w in words)) for key in WORDS] + [0.1]
            norm = math.sqrt(sum(x * x for x in vector))
            vectors.append([x / norm for x in vector])
        return vectors

    @staticmethod
    def name():
        return "word-counts"

    def get_config(self):
        return {}

    @staticmethod
    def build_from_config(config):
        return WordCounts()


def fresh_collection():
    return chromadb.EphemeralClient().create_collection(
        "notes-" + uuid.uuid4().hex[:8], embedding_function=WordCounts(), configuration={"hnsw": {"space": "cosine"}})


def tiny_pdf(pages):
    """A minimal valid PDF with one line of text per page, so pypdf can be tested without files."""
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", None, "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in pages:
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET"
        objects.append(f"<< /Length {len(stream)} >>\nstream\n{stream}\nendstream")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {len(objects)} 0 R >>")
        kids.append(f"{len(objects)} 0 R")
    objects[1] = f"<< /Type /Pages /Kids [{' '.join(kids)}] /Count {len(pages)} >>"
    out, offsets = b"%PDF-1.4\n", []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += f"{number} 0 obj\n{body}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode()
    out += "".join(f"{o:010d} 00000 n \n" for o in offsets).encode()
    out += f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


class ChunkTest(unittest.TestCase):
    def test_headings_stay_with_their_paragraph_and_chunks_fit(self):
        text = (HERE / "docs" / "library-handbook.md").read_text(encoding="utf-8")
        chunks = rag.chunk_text(text)
        self.assertTrue(all(len(c) <= rag.CHUNK_SIZE for c in chunks))
        self.assertTrue(any(c.startswith("## Late returns and lost items\nSince 1 March 2026") for c in chunks))
        self.assertFalse(any(c.endswith(("## Opening hours", "## Borrowing")) for c in chunks))

    def test_long_paragraphs_are_cut_at_sentence_ends(self):
        text = " ".join(f"Sentence number {n} is here." for n in range(40))
        chunks = rag.chunk_text(text, size=120)
        self.assertGreater(len(chunks), 5)
        self.assertTrue(all(c.endswith(".") and len(c) <= 120 for c in chunks))
        self.assertEqual(" ".join(chunks), text)

    def test_short_paragraphs_are_joined(self):
        self.assertEqual(rag.chunk_text("One.\n\nTwo.\n\n\n\nThree."), ["One.\nTwo.\nThree."])

    def test_headings_written_right_above_text_are_kept(self):
        text = "# Notes\n\n## Fees\nLate books cost\n20 cents a day.\n\n## Hours\n\nOpen 9 to 5."
        self.assertEqual(rag.chunk_text(text, size=60), ["# Notes\n## Fees\nLate books cost 20 cents a day.", "## Hours\nOpen 9 to 5."])


class IndexAndSearchTest(unittest.TestCase):
    def setUp(self):
        self.patch = mock.patch.object(rag, "notes", fresh_collection())
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.folder = Path(tempfile.mkdtemp())
        (self.folder / "handbook.md").write_text((HERE / "docs" / "library-handbook.md").read_text(encoding="utf-8"), encoding="utf-8")
        (self.folder / "papers").mkdir()
        (self.folder / "papers" / "wifi.pdf").write_bytes(tiny_pdf(["The wifi network is Riverside-Guest.", "Printing costs 10 cents a page."]))
        (self.folder / "ignored.docx").write_text("not read")

    def test_index_reads_markdown_and_pdf_pages(self):
        out = io.StringIO()
        with redirect_stdout(out):
            total = rag.index_folder(self.folder)
        self.assertEqual(total, rag.notes.count())
        self.assertIn("papers/wifi.pdf: 2 chunks", out.getvalue())
        self.assertNotIn("ignored", out.getvalue())
        pages = rag.notes.get(where={"source": "papers/wifi.pdf"})["metadatas"]
        self.assertEqual(sorted(m["page"] for m in pages), [1, 2])

    def test_indexing_again_replaces_old_chunks(self):
        with redirect_stdout(io.StringIO()):
            first = rag.index_folder(self.folder)
            (self.folder / "handbook.md").write_text("## Late returns\nThe charge is 20 cents a day.", encoding="utf-8")
            rag.index_folder(self.folder)
        self.assertEqual(rag.notes.count(), 3)
        self.assertLess(rag.notes.count(), first)

    def test_search_returns_closest_chunks_with_their_source(self):
        with redirect_stdout(io.StringIO()):
            rag.index_folder(self.folder)
        hits = rag.search("What is the charge if I return a book late?")
        self.assertTrue(hits[0]["text"].startswith("## Late returns and lost items"))
        self.assertEqual((hits[0]["source"], hits[0]["page"]), ("handbook.md", 1))
        self.assertLessEqual(len(hits), rag.TOP_K)
        self.assertEqual(hits, sorted(hits, key=lambda h: h["distance"]))
        self.assertEqual(rag.search("wifi")[0]["source"], "papers/wifi.pdf")

    def test_far_away_chunks_are_skipped(self):
        with redirect_stdout(io.StringIO()):
            rag.index_folder(self.folder)
        self.assertEqual(rag.search("Who founded the library in 1890?"), [])

    def test_empty_database_finds_nothing(self):
        self.assertEqual(rag.search("anything"), [])


class FakeMessages:
    def __init__(self):
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return NS(content=[NS(type="thinking", thinking=""), NS(type="text", text="20 cents a day [handbook.md, page 1].")],
                  usage=NS(input_tokens=400, output_tokens=30), stop_reason="end_turn")


class AnswerTest(unittest.TestCase):
    HITS = [{"source": "handbook.md", "page": 1, "text": "The charge is 20 cents a day.", "distance": 0.25}]

    def test_sources_go_in_tags_with_file_and_page(self):
        fake = FakeMessages()
        out = io.StringIO()
        with mock.patch.object(rag, "client", NS(messages=fake)), redirect_stdout(out):
            text = rag.answer("How much is the late charge?", self.HITS)
        self.assertEqual(text, "20 cents a day [handbook.md, page 1].")
        prompt = fake.calls[0]["messages"][0]["content"]
        self.assertIn('<source file="handbook.md" page="1">\nThe charge is 20 cents a day.\n</source>', prompt)
        self.assertTrue(prompt.endswith("Question: How much is the late charge?"))
        self.assertIn("[file, page N]", fake.calls[0]["system"])
        self.assertIn("[400 tokens in, 30 out, $0.00006]", out.getvalue())

    def test_no_hits_means_no_model_call(self):
        fake = FakeMessages()
        with mock.patch.object(rag, "client", NS(messages=fake)):
            text = rag.answer("Who founded the library?", [])
        self.assertEqual(text, "I couldn't find anything about that in your notes.")
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
