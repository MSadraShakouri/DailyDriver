# tests/test_qada_fasting_nudges.py
import sqlite3
import unittest
from datetime import datetime
from unittest.mock import patch

import jdatetime

from dailydriver.features.qada import _header
from dailydriver.features.qada._migrations import migrations


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

        # Patch get_connection_cm in _logic.py (where it's actually used)
        self.patcher = patch("dailydriver.features.qada._logic.get_connection_cm")
        self.mock_cm = self.patcher.start()
        self.mock_cm.return_value.__enter__.return_value = self.conn
        self.mock_cm.return_value.__exit__.return_value = False

    def tearDown(self):
        self.patcher.stop()
        self.conn.close()

    def test_nudge_shows_when_pending_today(self):
        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = self.today_j
            nudges = _header.get_fasting_nudges(self.conn, self.today_j)  # noqa: F841
            self.assertEqual(len(nudges), 1)
            self.assertIn("Ramadan fasting pending", nudges[0])

    def test_nudge_hides_when_logged_today(self):
        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date, amount) VALUES (?,?,?)",
            (self.entry_id, self.today_str, 1),
        )
        self.conn.commit()

        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = self.today_j
            nudges = _header.get_fasting_nudges(self.conn, self.today_j)  # noqa: F841
            self.assertEqual(nudges, [])

    def test_nudge_hides_when_declined_today(self):
        self.conn.execute(
            "INSERT INTO qada_declines (entry_id, instance_date) VALUES (?,?)",
            (self.entry_id, self.today_str),
        )
        self.conn.commit()

        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = self.today_j
            nudges = _header.get_fasting_nudges(self.conn, self.today_j)  # noqa: F841
            self.assertEqual(nudges, [])

    def test_nudge_does_not_show_for_past_date(self):
        yesterday = self.today_j - jdatetime.timedelta(days=1)
        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = yesterday
            nudges = _header.get_fasting_nudges(self.conn, yesterday)  # noqa: F841
            self.assertEqual(nudges, [])

    def test_nudge_does_not_show_for_future_date(self):
        tomorrow = self.today_j + jdatetime.timedelta(days=1)
        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = tomorrow
            nudges = _header.get_fasting_nudges(self.conn, tomorrow)  # noqa: F841
            self.assertEqual(nudges, [])

    def test_auto_no_writes_decline_after_midnight(self):
        yesterday = self.today_j - jdatetime.timedelta(days=1)

        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = yesterday

            now = datetime.now().replace(hour=0, minute=1, second=0)
            nudges = _header.get_fasting_nudges(self.conn, self.today_j, now=now)  # noqa: F841

            self.assertEqual(nudges, [])

            row = self.conn.execute(
                "SELECT instance_date FROM qada_declines WHERE entry_id=? AND instance_date=?",
                (self.entry_id, yesterday.strftime("%Y-%m-%d")),
            ).fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["instance_date"], yesterday.strftime("%Y-%m-%d"))

    def test_auto_no_does_not_overwrite_existing_decline(self):
        yesterday = self.today_j - jdatetime.timedelta(days=1)

        self.conn.execute(
            "INSERT INTO qada_declines (entry_id, instance_date) VALUES (?,?)",
            (self.entry_id, yesterday.strftime("%Y-%m-%d")),
        )
        self.conn.commit()

        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = yesterday

            now = datetime.now().replace(hour=0, minute=1, second=0)
            nudges = _header.get_fasting_nudges(self.conn, self.today_j, now=now)  # noqa: F841

            count = self.conn.execute(
                "SELECT COUNT(*) FROM qada_declines WHERE entry_id=? AND instance_date=?",
                (self.entry_id, yesterday.strftime("%Y-%m-%d")),
            ).fetchone()[0]
            self.assertEqual(count, 1)

    def test_auto_no_does_not_overwrite_existing_log(self):
        yesterday = self.today_j - jdatetime.timedelta(days=1)

        self.conn.execute(
            "INSERT INTO qada_logs (entry_id, instance_date, amount) VALUES (?,?,?)",
            (self.entry_id, yesterday.strftime("%Y-%m-%d"), 1),
        )
        self.conn.commit()

        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = yesterday

            now = datetime.now().replace(hour=0, minute=1, second=0)
            nudges = _header.get_fasting_nudges(self.conn, self.today_j, now=now)  # noqa: F841

            row = self.conn.execute(
                "SELECT 1 FROM qada_declines WHERE entry_id=? AND instance_date=?",
                (self.entry_id, yesterday.strftime("%Y-%m-%d")),
            ).fetchone()
            self.assertIsNone(row)

    def test_auto_no_handles_multiple_missed_days(self):
        five_days_ago = self.today_j - jdatetime.timedelta(days=5)

        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = five_days_ago

            now = datetime.now().replace(hour=0, minute=1, second=0)
            nudges = _header.get_fasting_nudges(self.conn, self.today_j, now=now)  # noqa: F841

            count = self.conn.execute(
                "SELECT COUNT(*) FROM qada_declines WHERE entry_id=?",
                (self.entry_id,),
            ).fetchone()[0]
            self.assertEqual(count, 5)

    def test_nudge_shows_after_auto_no_for_today(self):
        yesterday = self.today_j - jdatetime.timedelta(days=1)

        def mock_compute_side_effect(entry, target_date):
            if target_date == self.today_j:
                return self.today_j
            return yesterday

        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.side_effect = mock_compute_side_effect

            now = datetime.now().replace(hour=0, minute=1, second=0)
            nudges = _header.get_fasting_nudges(self.conn, self.today_j, now=now)  # noqa: F841

            self.assertEqual(len(nudges), 1)
            self.assertIn("Ramadan fasting pending", nudges[0])

    def test_no_nudge_if_entry_has_no_interval(self):
        self.conn.execute(
            "INSERT INTO qada_entries (name, kind, interval_type, target_total, logged_total) VALUES (?,?,?,?,?)",
            ("NoInterval", "fasting", None, 1, 0),
        )
        self.conn.commit()

        with patch("dailydriver.features.qada._header.compute_pending_instance") as mock_compute:
            mock_compute.return_value = self.today_j
            nudges = _header.get_fasting_nudges(self.conn, self.today_j)  # noqa: F841
            self.assertEqual(len(nudges), 1)
            self.assertIn("Ramadan", nudges[0])


if __name__ == "__main__":
    unittest.main()
