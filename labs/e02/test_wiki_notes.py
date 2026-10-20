"""Offline tests for wiki_notes.py. Wikipedia is faked, so no network is needed."""
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import httpx

sys.path.insert(0, str(Path(__file__).parent))
import wiki_notes  # noqa: E402

LLM = {
    "type": "standard",
    "title": "Large language model",
    "description": "Type of machine learning model",
    "extract": "A large language model (LLM) is a language model trained with self-supervised machine learning on a vast amount of text.",
    "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Large_language_model"}},
}
MERCURY = {
    "type": "disambiguation",
    "title": "Mercury",
    "extract": "Mercury may refer to:",
    "content_urls": {"desktop": {"page": "https://en.wikipedia.org/wiki/Mercury"}},
}
PAGES = {"Large_language_model": LLM, "Mercury": MERCURY, "C%2B%2B": dict(LLM, title="C++", description="")}
REDIRECTS = {"LLM": "Large_language_model"}


def fake_get(url, headers=None, timeout=None, follow_redirects=False):
    assert headers["User-Agent"] and timeout and follow_redirects
    key = url.rsplit("/", 1)[1]
    request = httpx.Request("GET", url)
    if key == "Offline":
        raise httpx.ConnectError("no internet", request=request)
    key = REDIRECTS.get(key, key)
    if key in PAGES:
        return httpx.Response(200, json=PAGES[key], request=request)
    return httpx.Response(404, json={"title": "Not found."}, request=request)


class WikiNotesTest(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.notes_file = Path(folder.name) / "notes.json"
        for patch in (mock.patch.object(wiki_notes, "NOTES_FILE", self.notes_file),
                      mock.patch.object(wiki_notes.httpx, "get", side_effect=fake_get)):
            patch.start()
            self.addCleanup(patch.stop)

    def run_main(self, *topics):
        out = io.StringIO()
        with redirect_stdout(out):
            wiki_notes.main(list(topics))
        return out.getvalue().splitlines()

    def saved(self):
        return json.loads(self.notes_file.read_text(encoding="utf-8"))

    def test_saves_a_note_with_the_fields_we_need(self):
        lines = self.run_main("Large language model")
        self.assertEqual(lines, ["Saved: Large language model (20 words)", f"Notes in {self.notes_file}: 1"])
        note = self.saved()[0]
        self.assertEqual(sorted(note), ["description", "saved_on", "summary", "title", "url"])
        self.assertEqual(note["url"], "https://en.wikipedia.org/wiki/Large_language_model")

    def test_redirect_counts_as_already_saved(self):
        self.run_main("Large language model")
        lines = self.run_main("LLM")
        self.assertEqual(lines[0], "Skipped: Large language model is already saved")
        self.assertEqual(len(self.saved()), 1)

    def test_errors_do_not_stop_the_run(self):
        lines = self.run_main("Qwxzzy", "Offline", "Large language model")
        self.assertEqual(lines[0], "Error: Qwxzzy: Wikipedia answered 404")
        self.assertEqual(lines[1], "Error: Offline: could not reach Wikipedia (ConnectError)")
        self.assertTrue(lines[2].startswith("Saved: Large language model"))

    def test_disambiguation_page_is_skipped(self):
        lines = self.run_main("Mercury")
        self.assertEqual(lines[0], "Skipped: Mercury has several meanings. Try a more specific title.")
        self.assertEqual(self.saved(), [])

    def test_titles_are_made_safe_for_the_url(self):
        lines = self.run_main("C++")
        self.assertTrue(lines[0].startswith("Saved: C++"))


if __name__ == "__main__":
    unittest.main()
