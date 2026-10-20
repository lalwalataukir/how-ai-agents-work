"""Milestone 1: read the diff"""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: no test calls Claude
sys.path.insert(0, str(Path(__file__).parent.parent))
import reviewer  # noqa: E402

HINT = ("Go through the diff line by line. A line starting with '+++ ' starts a new file; a line like "
        "'@@ -10,8 +12,15 @@' starts a hunk whose first line is line 12 of the new file. Inside a hunk, "
        "'+' and ' ' lines move the line number on by one, and '-' lines don't.")
SAMPLE = Path(__file__).parent.parent / "sample"
SMALL = """diff --git a/app.py b/app.py
--- a/app.py
+++ b/app.py
@@ -1 +1,2 @@
-print("hi")
+name = input("Name: ")
+print("hi", name)
\\ No newline at end of file
"""


class ParseDiffTest(unittest.TestCase):
    def setUp(self):
        self.changes = reviewer.parse_diff((SAMPLE / "changes.diff").read_text(encoding="utf-8"))
        self.by_path = {change.path: change for change in self.changes}

    def test_one_change_per_file_and_deleted_files_left_out(self):
        self.assertEqual([change.path for change in self.changes],
                         ["shop/accounts.py", "shop/cart.py", "shop/config.py", "shop/db.py", "shop/orders.py"])

    def test_added_lines_have_their_number_in_the_new_file(self):
        self.assertEqual(self.by_path["shop/cart.py"].added[17], "    for i in range(len(items) - 1):")
        self.assertEqual(sorted(self.by_path["shop/config.py"].added), [6, 8, 9])
        self.assertEqual(sorted(self.by_path["shop/orders.py"].added), list(range(11, 19)))

    def test_a_new_file_is_all_added_from_line_1(self):
        self.assertEqual(sorted(self.by_path["shop/accounts.py"].added), list(range(1, 19)))

    def test_removed_lines_are_kept_without_a_number(self):
        self.assertIn(("-", None, 'PAYGATE_SECRET = os.environ["PAYGATE_SECRET"]'), self.by_path["shop/config.py"].rows)

    def test_context_lines_are_numbered_too(self):
        self.assertIn((" ", 7, "RESET_LINK_HOURS = 2  # how long a password reset link works"), self.by_path["shop/config.py"].rows)

    def test_a_gap_row_between_two_hunks(self):
        self.assertEqual(self.by_path["shop/cart.py"].rows.count(("@", None, "")), 1)

    def test_hunk_headers_without_counts_and_no_newline_markers(self):
        [change] = reviewer.parse_diff(SMALL)
        self.assertEqual(change.rows, [("-", None, 'print("hi")'), ("+", 1, 'name = input("Name: ")'), ("+", 2, 'print("hi", name)')])

    def test_an_empty_diff_has_no_changes(self):
        self.assertEqual(reviewer.parse_diff(""), [])


class FormatTest(unittest.TestCase):
    def test_each_row_shows_its_mark_and_line_number(self):
        [change] = reviewer.parse_diff(SMALL)
        self.assertEqual(reviewer.format_change(change), '<file path="app.py">\n'
                                                         '-      | print("hi")\n'
                                                         '+    1 | name = input("Name: ")\n'
                                                         '+    2 | print("hi", name)\n'
                                                         '</file>')

    def test_a_gap_between_hunks_shows_as_dots(self):
        changes = reviewer.parse_diff((SAMPLE / "changes.diff").read_text(encoding="utf-8"))
        self.assertIn("\n       ...\n", reviewer.format_change(changes[1]))

    def test_the_prompt_has_every_file(self):
        changes = reviewer.parse_diff((SAMPLE / "changes.diff").read_text(encoding="utf-8"))
        prompt = reviewer.build_prompt(changes)
        self.assertEqual(prompt.count("<file path="), 5)
        self.assertIn("+   25 |             f\"SELECT", prompt)


if __name__ == "__main__":
    unittest.main()
