"""E4 lab: turn an article into checked, structured data.

Run it with:
    uv run extract.py article.txt
"""
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

MODEL = "claude-haiku-5-5"
client = anthropic.Anthropic()


class Claim(BaseModel):
    claim: str  # the claim, in one sentence
    quote: str  # the exact words in the article that support it


class Extract(BaseModel):
    title: str
    claims: list[Claim]
    sources: list[str]  # people, organisations or documents the article cites


PROMPT = """Extract the key facts from the article below.

Rules:
- title: the article's headline, or a short title if it has none.
- claims: the 3 to 5 most important factual claims. Write each claim in one sentence,
  and copy the exact words from the article that support it into quote.
- sources: every person, organisation or document the article cites. Use an empty list if none.

<article>
{article}
</article>"""


def check(result, article):
    """Rules the schema can't enforce. Returns a list of problems; an empty list means all good."""
    problems = []
    if not 3 <= len(result.claims) <= 5:
        problems.append(f"There are {len(result.claims)} claims. Give 3 to 5.")
    text = " ".join(article.split())  # ignore differences in line breaks and spacing
    for item in result.claims:
        if " ".join(item.quote.split()) not in text:
            problems.append(f"This quote is not in the article word for word: {item.quote!r}")
    return problems


def extract(article, attempts=2):
    """Ask for structured data, check it, and ask again with the problems listed if it fails."""
    messages = [{"role": "user", "content": PROMPT.format(article=article)}]
    for attempt in range(1, attempts + 1):
        response = client.messages.parse(
            model=MODEL,
            max_tokens=4000,
            messages=messages,
            output_format=Extract,  # the API guarantees JSON in this shape
            output_config={"effort": "low"},
        )
        if response.stop_reason != "end_turn":  # cut off or declined: no complete answer
            raise RuntimeError(f"The model stopped early ({response.stop_reason}).")
        result = response.parsed_output  # an Extract object, already validated
        problems = check(result, article)
        if not problems:
            print(f"Checks passed on attempt {attempt}.")
            return result
        print(f"Attempt {attempt}: {len(problems)} problem(s). Asking again.")
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": "Fix these problems and answer again:\n" + "\n".join(problems)})
    raise ValueError("Still failing the checks:\n" + "\n".join(problems))


def main(path):
    article = Path(path).read_text(encoding="utf-8")
    result = extract(article)
    output = result.model_dump_json(indent=2)
    print(output)
    Path("extract.json").write_text(output, encoding="utf-8")
    print("Saved to extract.json")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "article.txt")
