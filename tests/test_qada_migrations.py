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
        for t in ("qada_entries", "qada_logs", "qada_declines"):
            self.assertIn(t, tables)

    def test_qada_logs_cascade_on_entry_delete(self):
        self.conn.execute("INSERT INTO qada_entries (name, kind) VALUES ('test', 'prayer')")
        entry_id = self.conn.execute("SELECT id FROM qada_entries WHERE name='test'").fetchone()["id"]
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date) VALUES (?, '1405-01-01')",
            (entry_id,),
        )
        # delete the entry
        self.conn.execute("DELETE FROM qada_entries WHERE id=?", (entry_id,))
        logs = self.conn.execute("SELECT COUNT(*) FROM qada_logs WHERE entry_id=?", (entry_id,)).fetchone()[0]
        self.assertEqual(logs, 0)

    def test_qada_declines_cascade_on_entry_delete(self):
        self.conn.execute("INSERT INTO qada_entries (name, kind) VALUES ('test', 'fasting')")
        entry_id = self.conn.execute("SELECT id FROM qada_entries WHERE name='test'").fetchone()["id"]
        self.conn.execute(
            "INSERT INTO qada_declines (entry_id, instance_date) VALUES (?, '1405-01-01')",
            (entry_id,),
        )
        self.conn.execute("DELETE FROM qada_entries WHERE id=?", (entry_id,))
        declines = self.conn.execute("SELECT COUNT(*) FROM qada_declines WHERE entry_id=?", (entry_id,)).fetchone()[0]
        self.assertEqual(declines, 0)

    def test_multiple_logs_same_instance_allowed(self):
        self.conn.execute("INSERT INTO qada_entries (name, kind) VALUES ('test', 'prayer')")
        entry_id = self.conn.execute("SELECT id FROM qada_entries WHERE name='test'").fetchone()["id"]
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date) VALUES (?, '1405-01-01')",
            (entry_id,),
        )
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date) VALUES (?, '1405-01-01')",
            (entry_id,),
        )
        count = self.conn.execute(
            "SELECT COUNT(*) FROM qada_logs WHERE entry_id=? AND instance_date=?",
            (entry_id, "1405-01-01"),
        ).fetchone()[0]
        self.assertEqual(count, 2)


if __name__ == "__main__":
    unittest.main()
