"""E2 lab: save short Wikipedia summaries as notes.

Run it with one or more topics:
    uv run wiki_notes.py "Large language model" "Prompt engineering"
"""
import json
import sys
from datetime import date
from pathlib import Path
from urllib.parse import quote

import httpx

API_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/"
# Wikipedia asks every script to say who it is. Put your email or GitHub link here.
HEADERS = {"User-Agent": "research-assistant/0.1 (you@example.com)"}
NOTES_FILE = Path("notes.json")


def fetch_summary(topic):
    """Ask Wikipedia for a short summary of one topic. Returns the JSON as a dict."""
    url = API_URL + quote(topic.replace(" ", "_"))
    response = httpx.get(url, headers=HEADERS, timeout=10, follow_redirects=True)
    response.raise_for_status()  # turns answers like 404 into an error
    return response.json()


def make_note(data):
    """Keep only the fields we need from Wikipedia's answer."""
    return {
        "title": data["title"],
        "description": data.get("description", ""),
        "summary": data["extract"],
        "url": data["content_urls"]["desktop"]["page"],
        "saved_on": date.today().isoformat(),
    }


def load_notes():
    """Read the notes saved so far, or start with an empty list."""
    if NOTES_FILE.exists():
        return json.loads(NOTES_FILE.read_text(encoding="utf-8"))
    return []


def save_notes(notes):
    NOTES_FILE.write_text(json.dumps(notes, indent=2, ensure_ascii=False), encoding="utf-8")


def already_saved(notes, title):
    for note in notes:
        if note["title"] == title:
            return True
    return False


def main(topics):
    notes = load_notes()
    for topic in topics:
        try:
            data = fetch_summary(topic)
        except httpx.HTTPStatusError as error:
            print(f"Error: {topic}: Wikipedia answered {error.response.status_code}")
            continue
        except httpx.RequestError as error:
            print(f"Error: {topic}: could not reach Wikipedia ({type(error).__name__})")
            continue

        if data.get("type") == "disambiguation":
            print(f"Skipped: {topic} has several meanings. Try a more specific title.")
            continue

        note = make_note(data)
        if already_saved(notes, note["title"]):
            print(f"Skipped: {note['title']} is already saved")
            continue

        notes.append(note)
        words = len(note["summary"].split())
        print(f"Saved: {note['title']} ({words} words)")

    save_notes(notes)
    print(f"Notes in {NOTES_FILE}: {len(notes)}")


if __name__ == "__main__":
    topics = sys.argv[1:]  # everything typed after the file name
    if not topics:
        topics = ["Large language model"]
    main(topics)
