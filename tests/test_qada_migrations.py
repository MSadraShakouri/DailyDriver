# tests/test_qada_migrations.py
import sqlite3
import unittest

from dailydriver.features.qada._migrations import migrations


class TestQadaMigrations(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)

    def tearDown(self):
        self.conn.close()

    def test_all_tables_exist(self):
        tables = {
            row["name"] for row in self.conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        }
        for t in ("qada_entries", "qada_logs"):
            self.assertIn(t, tables)
        self.assertNotIn("qada_declines", tables)

    def test_qada_entries_has_correct_columns(self):
        cur = self.conn.execute("PRAGMA table_info(qada_entries)")
        columns = [row["name"] for row in cur.fetchall()]
        expected = {
            "id",
            "name",
            "kind",
            "interval_type",
            "interval_value",
            "interval_calendar",
            "paused_until",
            "created_at",
            "slot",
            "target_total",
            "logged_total",
        }
        # paused_from should NOT be present
        self.assertNotIn("paused_from", columns)
        self.assertTrue(expected.issubset(set(columns)))


if __name__ == "__main__":
    unittest.main()
