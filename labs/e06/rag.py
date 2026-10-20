"""E6 lab: ask questions over your own notes and PDFs, and get answers with citations.

Run it with:
    uv run rag.py index docs                  # read every file in docs/ into the database
    uv run rag.py search "late fees"          # see what retrieval finds (free: no model call)
    uv run rag.py ask "How much is the fine for a late book?"
"""
import sys
from pathlib import Path

import anthropic
import chromadb
from dotenv import load_dotenv
from pypdf import PdfReader

load_dotenv()

MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10, 0.50  # dollars per million tokens, for this model
CHUNK_SIZE = 500     # most characters in one chunk, about 125 tokens
TOP_K = 4            # how many chunks to give the model
MAX_DISTANCE = 0.75  # skip chunks further than this from the question (0 = same meaning, 1 = unrelated)
SYSTEM = (
    "Answer the question using only the sources below. After each fact, cite the source it came from "
    "as [file, page N]. If the sources don't contain the answer, say you couldn't find it in the notes. "
    "Answer in at most 150 words."
)

client = anthropic.Anthropic()
db = chromadb.PersistentClient(path=Path(__file__).parent / "chroma")  # a folder next to this file
notes = db.get_or_create_collection("notes", configuration={"hnsw": {"space": "cosine"}})


def read_file(path):
    """Return a list of (page number, text). A text or Markdown file counts as one page."""
    if path.suffix.lower() == ".pdf":
        return [(number, page.extract_text() or "") for number, page in enumerate(PdfReader(path).pages, 1)]
    return [(1, path.read_text(encoding="utf-8"))]


def chunk_text(text, size=CHUNK_SIZE):
    """Split text into chunks of at most `size` characters, keeping paragraphs and sentences whole."""
    pieces, heading = [], ""
    for paragraph in text.split("\n\n"):
        lines = paragraph.strip().split("\n")
        if lines[0].startswith("#"):  # a Markdown heading: keep it with the text below it
            heading = (heading + "\n" + lines.pop(0).strip()).strip()
        paragraph = " ".join(" ".join(lines).split())  # tidy line breaks and spaces
        if not paragraph:
            continue
        if heading:
            paragraph, heading = heading + "\n" + paragraph, ""
        while len(paragraph) > size:  # too long: cut at the last sentence end that fits
            cut = paragraph.rfind(". ", 0, size)
            cut = cut + 1 if cut > 0 else size
            pieces.append(paragraph[:cut].strip())
            paragraph = paragraph[cut:].strip()
        if paragraph:
            pieces.append(paragraph)
    chunks = []
    for piece in pieces:  # join short pieces until a chunk is full
        if chunks and len(chunks[-1]) + 1 + len(piece) <= size:
            chunks[-1] += "\n" + piece
        else:
            chunks.append(piece)
    return chunks


def index_file(path, folder):
    """Chunk one file and store the chunks. Indexing a file again replaces its old chunks."""
    source = path.relative_to(folder).as_posix()
    notes.delete(where={"source": source})
    count = 0
    for page, text in read_file(path):
        chunks = chunk_text(text)
        if chunks:
            notes.add(
                ids=[f"{source}:{page}:{n}" for n in range(len(chunks))],
                documents=chunks,  # Chroma turns each chunk into an embedding as it stores it
                metadatas=[{"source": source, "page": page} for _ in chunks],
            )
            count += len(chunks)
    return count


def index_folder(folder):
    """Index every .md, .txt and .pdf file in a folder and the folders inside it."""
    folder = Path(folder)
    total = 0
    for path in sorted(folder.rglob("*")):
        if path.suffix.lower() in (".md", ".txt", ".pdf"):
            count = index_file(path, folder)
            print(f"  {path.relative_to(folder)}: {count} chunks")
            total += count
    return total


def search(question, k=TOP_K):
    """The k chunks closest in meaning to the question, skipping any that are too far away."""
    if notes.count() == 0:
        return []
    found = notes.query(query_texts=[question], n_results=min(k, notes.count()))
    hits = []
    for text, meta, distance in zip(found["documents"][0], found["metadatas"][0], found["distances"][0]):
        if distance <= MAX_DISTANCE:
            hits.append({"source": meta["source"], "page": meta["page"], "text": text, "distance": round(distance, 2)})
    return hits


def answer(question, hits):
    """Ask Claude to answer the question from the retrieved chunks."""
    if not hits:  # nothing close enough: say so, and don't pay for a model call
        return "I couldn't find anything about that in your notes."
    sources = "\n".join(
        f'<source file="{hit["source"]}" page="{hit["page"]}">\n{hit["text"]}\n</source>' for hit in hits
    )
    response = client.messages.create(
        model=MODEL, max_tokens=2000, system=SYSTEM, output_config={"effort": "low"},
        messages=[{"role": "user", "content": f"<sources>\n{sources}\n</sources>\n\nQuestion: {question}"}],
    )
    cost = (response.usage.input_tokens * PRICE_IN + response.usage.output_tokens * PRICE_OUT) / 1_000_000
    print(f"  [{response.usage.input_tokens} tokens in, {response.usage.output_tokens} out, ${cost:.5f}]\n")
    return "".join(block.text for block in response.content if block.type == "text")


def show(hits):
    for hit in hits:
        preview = hit["text"].replace("\n", " ")[:70]
        print(f"  {hit['distance']:.2f}  {hit['source']}, page {hit['page']}: {preview}...")


def main(args):
    if len(args) == 2 and args[0] == "index":
        total = index_folder(args[1])
        print(f"Indexed {total} chunks. The database holds {notes.count()}.")
    elif len(args) >= 2 and args[0] in ("search", "ask"):
        question = " ".join(args[1:])
        hits = search(question)
        if hits:
            show(hits)
        else:
            print("  Nothing close enough in your notes.")
        if args[0] == "ask":
            print(answer(question, hits))
    else:
        print(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
