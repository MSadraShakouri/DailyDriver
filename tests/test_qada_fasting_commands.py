# tests/test_qada_fasting_commands.py
import sqlite3
import unittest
from unittest.mock import patch

import jdatetime

from dailydriver.features.qada import _logic
from dailydriver.features.qada._migrations import migrations


class TestQadaFastingCommands(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)
        self.today = jdatetime.date.today().strftime("%Y-%m-%d")
        self.entry_id = self._add_fasting_entry()

        # Patch get_connection_cm to return our connection
        self.patcher = patch("dailydriver.features.qada._logic.get_connection_cm")
        self.mock_cm = self.patcher.start()
        self.mock_cm.return_value.__enter__.return_value = self.conn
        self.mock_cm.return_value.__exit__.return_value = False

    def tearDown(self):
        self.patcher.stop()
        self.conn.close()

    def _add_fasting_entry(self, name="Ramadan", interval_type="daily", target_total=1):
        self.conn.execute(
            "INSERT INTO qada_entries (name, kind, interval_type, target_total, logged_total) VALUES (?,?,?,?,?)",
            (name, "fasting", interval_type, target_total, 0),
        )
        self.conn.commit()
        return self.conn.execute("SELECT id FROM qada_entries WHERE name=?", (name,)).fetchone()["id"]

    def test_log_fasting_inserts_log(self):
        result = _logic.log_fasting(self.entry_id)  # noqa: F841
        self.assertIn("1/1 (100.000%)", result)
        row = self.conn.execute(
            "SELECT amount, instance_date FROM qada_logs WHERE entry_id=?",
            (self.entry_id,),
        ).fetchone()
        self.assertEqual(row["amount"], 1)
        self.assertEqual(row["instance_date"], self.today)

    def test_log_fasting_fails_if_decline_exists(self):
        # First decline
        _logic.decline_fasting(self.entry_id)
        # Then try to log – should fail
        result = _logic.log_fasting(self.entry_id)
        self.assertIn("Cannot log: you already declined today", result)
        # No log row should exist
        row = self.conn.execute(
            "SELECT 1 FROM qada_logs WHERE entry_id=? AND instance_date=?",
            (self.entry_id, self.today),
        ).fetchone()
        self.assertIsNone(row)
        # Decline should still exist
        row = self.conn.execute(
            "SELECT 1 FROM qada_declines WHERE entry_id=? AND instance_date=?",
            (self.entry_id, self.today),
        ).fetchone()
        self.assertIsNotNone(row)

    def test_decline_fasting_inserts_decline(self):
        result = _logic.decline_fasting(self.entry_id)  # noqa: F841
        self.assertIn("Fasting declined", result)
        row = self.conn.execute(
            "SELECT instance_date FROM qada_declines WHERE entry_id=? AND instance_date=?",
            (self.entry_id, self.today),
        ).fetchone()
        self.assertEqual(row["instance_date"], self.today)

    def test_decline_fasting_is_idempotent(self):
        _logic.decline_fasting(self.entry_id)
        _logic.decline_fasting(self.entry_id)
        count = self.conn.execute(
            "SELECT COUNT(*) FROM qada_declines WHERE entry_id=? AND instance_date=?",
            (self.entry_id, self.today),
        ).fetchone()[0]
        self.assertEqual(count, 1)

    def test_qada_fasting_yes_parses(self):
        with patch("dailydriver.features.qada._logic.log_fasting") as mock_log:
            mock_log.return_value = "Logged"
            result = _logic._parse_fasting("yes")  # noqa: F841
            mock_log.assert_called_once_with(self.entry_id)

    def test_qada_fasting_no_parses(self):
        with patch("dailydriver.features.qada._logic.decline_fasting") as mock_decline:
            mock_decline.return_value = "Declined"
            result = _logic._parse_fasting("no")  # noqa: F841
            mock_decline.assert_called_once_with(self.entry_id)

    def test_qada_fasting_invalid_returns_usage(self):
        result = _logic._parse_fasting("maybe")
        self.assertEqual(result, "Usage: qada fasting yes | qada fasting no")

    def test_qada_fasting_empty_returns_usage(self):
        result = _logic._parse_fasting("")
        self.assertEqual(result, "Usage: qada fasting yes | qada fasting no")

    def test_qada_fasting_no_entry_returns_error(self):
        # Delete the entry
        self.conn.execute("DELETE FROM qada_entries WHERE id=?", (self.entry_id,))
        self.conn.commit()
        result = _logic._parse_fasting("yes")
        self.assertEqual(result, "No fasting entry found. Add one first.")

    def test_log_fasting_uses_specified_now(self):
        fake_now = 1234567890
        result = _logic.log_fasting(self.entry_id, now=fake_now)  # noqa: F841
        row = self.conn.execute(
            "SELECT logged_at FROM qada_logs WHERE entry_id=? AND instance_date=?",
            (self.entry_id, self.today),
        ).fetchone()
        self.assertEqual(row["logged_at"], fake_now)

    def test_decline_fasting_uses_specified_now(self):
        fake_now = 9876543210
        result = _logic.decline_fasting(self.entry_id, now=fake_now)  # noqa: F841
        row = self.conn.execute(
            "SELECT logged_at FROM qada_declines WHERE entry_id=? AND instance_date=?",
            (self.entry_id, self.today),
        ).fetchone()
        self.assertEqual(row["logged_at"], fake_now)


if __name__ == "__main__":
    unittest.main()
