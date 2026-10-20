"""Milestone 1: know the data"""
import os
import sys
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: no test calls Claude
sys.path.insert(0, str(Path(__file__).parent.parent))
import analyst  # noqa: E402
from fakes import test_db  # noqa: E402

HINT = ("SELECT name FROM sqlite_master WHERE type = 'table' lists the tables; PRAGMA table_info(\"orders\") gives "
        "each column's name and type. For TEXT columns, SELECT DISTINCT ... LIMIT 9: if 8 or fewer come back, list them.")


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.text = analyst.describe_schema(test_db())
        self.lines = self.text.splitlines()

    def test_every_table_with_its_row_count(self):
        tables = [line for line in self.lines if not line.startswith(" ")]
        self.assertEqual(tables, ["customers (300 rows)", "products (40 rows)", "orders (2000 rows)", "order_items (3771 rows)"])

    def test_every_column_with_its_type(self):
        self.assertIn("  id INTEGER", self.lines)
        self.assertIn("  price_cents INTEGER", self.lines)
        self.assertIn("  quantity INTEGER", self.lines)
        self.assertEqual(sum(line.startswith("  ") for line in self.lines), 4 + 4 + 4 + 4)

    def test_short_lists_of_values_are_shown(self):
        self.assertIn("  status TEXT: cancelled, completed, refunded", self.lines)
        self.assertIn("  region TEXT: East, North, South, West", self.lines)
        self.assertIn("  category TEXT: Books, Games, Garden, Home, Toys", self.lines)

    def test_long_lists_are_not(self):
        self.assertIn("  name TEXT", self.lines)
        self.assertIn("  ordered_at TEXT", self.lines)

    def test_the_schema_goes_in_the_system_prompt(self):
        self.assertIn("{schema}", analyst.SYSTEM)


if __name__ == "__main__":
    unittest.main()
