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

    def _add_fasting_entry(self, name="Ramadan", interval_type="daily", target_total=1, created_at=None):
        if created_at is None:
            self.conn.execute(
                "INSERT INTO qada_entries (name, kind, interval_type, target_total, logged_total) VALUES (?,?,?,?,?)",
                (name, "fasting", interval_type, target_total, 0),
            )
        else:
            self.conn.execute(
                "INSERT INTO qada_entries (name, kind, interval_type, target_total, logged_total, created_at) VALUES (?,?,?,?,?,?)",
                (name, "fasting", interval_type, target_total, 0, created_at),
            )
        self.conn.commit()
        return self.conn.execute("SELECT id FROM qada_entries WHERE name=?", (name,)).fetchone()["id"]

    def test_log_fasting_inserts_log(self):
        today_start = int(jdatetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        eid = self._add_fasting_entry(created_at=today_start)
        result = _logic.log_fasting(eid)
        self.assertIn("1/1 (100.000%)", result)
        row = self.conn.execute(
            "SELECT amount, instance_date FROM qada_logs WHERE entry_id=?",
            (eid,),
        ).fetchone()
        self.assertEqual(row["amount"], 1)
        self.assertEqual(row["instance_date"], self.today)

    def test_log_fasting_uses_specified_now(self):
        today_start = int(jdatetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        eid = self._add_fasting_entry(created_at=today_start)
        fake_now = 1234567890
        _logic.log_fasting(eid, now=fake_now)
        row = self.conn.execute(
            "SELECT logged_at FROM qada_logs WHERE entry_id=? AND instance_date=?",
            (eid, self.today),
        ).fetchone()
        self.assertEqual(row["logged_at"], fake_now)

    def test_log_fasting_without_target(self):
        # Create entry with target=-1 (unbounded)
        eid = self._add_fasting_entry(name="Unbounded", target_total=-1)
        result = _logic.log_fasting(eid)
        self.assertIn("1/∞", result)
        row = self.conn.execute(
            "SELECT logged_total FROM qada_entries WHERE id=?",
            (eid,),
        ).fetchone()
        self.assertEqual(row["logged_total"], 1)

    def test_qada_fasting_yes_parses(self):
        with patch("dailydriver.features.qada._logic.log_fasting") as mock_log:
            mock_log.return_value = "Logged"
            result = _logic._parse_fasting("yes")
            mock_log.assert_called_once_with(self.entry_id)
            self.assertEqual(result, "Logged")

    def test_qada_fasting_no_parses_to_pause(self):
        with patch("dailydriver.features.qada._logic.pause_fasting_entry") as mock_pause:
            mock_pause.return_value = "Paused"
            result = _logic._parse_fasting("no")
            mock_pause.assert_called_once()
            self.assertEqual(result, "Paused")

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


if __name__ == "__main__":
    unittest.main()
