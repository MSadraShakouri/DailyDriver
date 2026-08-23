# tests/test_qada_fasting_nudges.py
import sqlite3
import unittest
from datetime import datetime
from unittest.mock import patch

import jdatetime

from dailydriver.features.qada import header
from dailydriver.features.qada.migrations import migrations


class TestQadaFastingNudges(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)

        self.today_j = jdatetime.date.today()
        self.today_str = self.today_j.strftime("%Y-%m-%d")

        # Add a fasting entry
        self.conn.execute(
            "INSERT INTO qada_entries (name, kind, interval_type, target_total, logged_total) VALUES (?,?,?,?,?)",
            ("Ramadan", "fasting", "daily", 1, 0),
        )
        self.conn.commit()
        self.entry_id = self.conn.execute("SELECT id FROM qada_entries WHERE name='Ramadan'").fetchone()["id"]

        # Patch get_connection_cm in _logic.py (used by list_entries)
        self.patcher = patch("dailydriver.features.qada.entries.get_connection_cm")
        self.mock_cm = self.patcher.start()
        self.mock_cm.return_value.__enter__.return_value = self.conn
        self.mock_cm.return_value.__exit__.return_value = False

    def tearDown(self):
        self.patcher.stop()
        self.conn.close()

    def test_nudge_shows_when_pending_today(self):
        with patch("dailydriver.features.qada.header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = self.today_j
            nudges = header.get_fasting_nudges(self.conn, self.today_j)
            self.assertEqual(len(nudges), 1)
            self.assertIn("🌙 Fasting pending", nudges[0])

    def test_nudge_hides_when_logged_today(self):
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date, amount) VALUES (?,?,?)",
            (self.entry_id, self.today_str, 1),
        )
        self.conn.commit()

        with patch("dailydriver.features.qada.header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = self.today_j
            nudges = header.get_fasting_nudges(self.conn, self.today_j)
            self.assertEqual(nudges, [])

    def test_nudge_shows_overdue(self):
        yesterday = self.today_j - jdatetime.timedelta(days=1)
        with patch("dailydriver.features.qada.header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = yesterday
            nudges = header.get_fasting_nudges(self.conn, self.today_j)
            self.assertEqual(len(nudges), 1)
            self.assertIn("🌙 Fasting overdue!", nudges[0])

    def test_nudge_does_not_show_for_future_date(self):
        tomorrow = self.today_j + jdatetime.timedelta(days=1)
        with patch("dailydriver.features.qada.header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = tomorrow
            nudges = header.get_fasting_nudges(self.conn, self.today_j)
            self.assertEqual(nudges, [])

    def test_nudge_hides_if_paused(self):
        # Pause the entry
        self.conn.execute(
            "UPDATE qada_entries SET paused_until = ? WHERE id = ?",
            ((self.today_j + jdatetime.timedelta(days=1)).strftime("%Y-%m-%d"), self.entry_id),
        )
        self.conn.commit()

        with patch("dailydriver.features.qada.header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = self.today_j
            nudges = header.get_fasting_nudges(self.conn, self.today_j)
            self.assertEqual(nudges, [])

    def test_nudge_shows_not_set_for_unbounded(self):
        # Create entry with target=-1
        self.conn.execute(
            "INSERT INTO qada_entries (name, kind, interval_type, target_total, logged_total) VALUES (?,?,?,?,?)",
            ("Unbounded", "fasting", "daily", -1, 0),
        )
        self.conn.commit()
        unbounded_id = self.conn.execute("SELECT id FROM qada_entries WHERE name='Unbounded'").fetchone()["id"]

        with patch("dailydriver.features.qada.header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = self.today_j
            nudges = header.get_fasting_nudges(self.conn, self.today_j)
            # Should show "not set" for unbounded
            self.assertTrue(any("not set" in n for n in nudges))


if __name__ == "__main__":
    unittest.main()
