"""Milestone 2: a safe SQL tool"""
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("ANTHROPIC_API_KEY", "test-key")  # never used: no test calls Claude
sys.path.insert(0, str(Path(__file__).parent.parent))
import analyst  # noqa: E402
from fakes import test_db  # noqa: E402

HINT = ("Connect with sqlite3.connect(Path(db).resolve().as_uri() + \"?mode=ro\", uri=True), then "
        "conn.set_authorizer(only_reads). A progress handler that returns True once a deadline passes stops a slow "
        "query. Catch sqlite3.Error and raise ValueError with a message that says what to do instead.")
FOREVER = "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n) SELECT COUNT(*) FROM n"


class ReadTest(unittest.TestCase):
    def test_a_query_returns_columns_and_rows(self):
        data = analyst.run_sql(test_db(), "SELECT region, COUNT(*) AS customers FROM customers GROUP BY region ORDER BY region")
        self.assertEqual(data["columns"], ["region", "customers"])
        self.assertEqual([row[0] for row in data["rows"]], ["East", "North", "South", "West"])
        self.assertFalse(data["truncated"])

    def test_big_results_are_cut_to_max_rows(self):
        data = analyst.run_sql(test_db(), "SELECT id FROM orders")
        self.assertEqual((len(data["rows"]), data["truncated"]), (analyst.MAX_ROWS, True))
        self.assertEqual(len(analyst.run_sql(test_db(), "SELECT id FROM orders", max_rows=5)["rows"]), 5)

    def test_joins_and_recursive_queries_are_fine(self):
        data = analyst.run_sql(test_db(), "WITH RECURSIVE n(i) AS (SELECT 1 UNION ALL SELECT i + 1 FROM n WHERE i < 3) SELECT SUM(i) FROM n")
        self.assertEqual(data["rows"], [[6]])


class AttackTest(unittest.TestCase):
    """Each of these must fail with a ValueError, and leave the database as it was."""

    def setUp(self):
        self.db = Path(tempfile.mkdtemp()) / "shop.db"
        shutil.copy(test_db(), self.db)
        self.before = self.db.read_bytes()

    def refused(self, sql):
        with self.assertRaises(ValueError, msg=sql):
            analyst.run_sql(self.db, sql)
        self.assertEqual(self.db.read_bytes(), self.before, sql)

    def test_nothing_can_be_changed(self):
        for sql in ("DROP TABLE orders", "DELETE FROM orders", "UPDATE products SET price_cents = 1",
                    "INSERT INTO customers (name, region, joined) VALUES ('x', 'x', 'x')",
                    "CREATE TABLE notes (x)", "ALTER TABLE orders ADD COLUMN x"):
            self.refused(sql)

    def test_no_other_files_or_settings(self):
        for sql in ("ATTACH DATABASE 'other.db' AS other", "PRAGMA writable_schema = ON", "SELECT load_extension('x')", "VACUUM"):
            self.refused(sql)
        self.assertFalse((self.db.parent / "other.db").exists())

    def test_one_statement_at_a_time(self):
        self.refused("SELECT 1; DROP TABLE orders")

    def test_a_query_that_never_ends_is_stopped(self):
        with self.assertRaises(ValueError) as caught:
            analyst.run_sql(self.db, FOREVER, seconds=0.3)
        self.assertIn("longer than", str(caught.exception))

    def test_mistakes_explain_themselves(self):
        with self.assertRaises(ValueError) as caught:
            analyst.run_sql(self.db, "SELECT nope FROM orders")
        self.assertIn("no such column", str(caught.exception))

    def test_a_missing_database_says_how_to_make_it(self):
        with self.assertRaises(ValueError) as caught:
            analyst.run_sql(self.db.parent / "missing.db", "SELECT 1")
        self.assertIn("make_data.py", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
