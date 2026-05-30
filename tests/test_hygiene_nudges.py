# tests/test_hygiene_nudges.py
import sqlite3
import unittest
from datetime import datetime
from unittest.mock import patch

import jdatetime

from dailydriver.features.hygiene._header import compute_hygiene_nudges


class TestHygieneNudges(unittest.TestCase):
    def setUp(self):
        # In‑memory DB with hygiene_config table
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE hygiene_config (id INTEGER PRIMARY KEY, item TEXT UNIQUE,"
            "desired_interval_days INTEGER, early_warning_enabled INTEGER DEFAULT 1,"
            "show_due_today INTEGER DEFAULT 1)"
        )
        self.conn.commit()

        # Fixed target date: 30 Ordibehesht 1405 (Gregorian: 2026-05-20)
        self.today_j = jdatetime.date(1405, 2, 30)
        self.today_g = self.today_j.togregorian()  # datetime.date(2026,5,20)

    def tearDown(self):
        self.conn.close()

    # ---------- helpers ----------
    def _insert_item(self, item, interval, early=1, due_today=1):
        self.conn.execute(
            "INSERT INTO hygiene_config (item, desired_interval_days, early_warning_enabled, show_due_today)"
            " VALUES (?,?,?,?)",
            (item, interval, early, due_today),
        )
        self.conn.commit()

    def _set_last_time(self, item, delta_days):
        """Mock get_last_hygiene_time to return a timestamp *delta_days* before today."""
        ts = (
            int(datetime(self.today_g.year, self.today_g.month, self.today_g.day, 12, 0, 0).timestamp())
            - delta_days * 86400
        )
        return ts

    @patch("dailydriver.features.hygiene._header.get_last_hygiene_time")
    def test_overdue(self, mock_last):
        self._insert_item("shower", 7)
        # last log 8 days ago
        mock_last.return_value = self._set_last_time("shower", 8)
        nudges = compute_hygiene_nudges(self.conn, relative_to=self.today_j)
        self.assertEqual(len(nudges), 1)
        self.assertIn("shower", nudges[0])
        self.assertIn("overdue", nudges[0])
        self.assertIn("8d ago", nudges[0])

    @patch("dailydriver.features.hygiene._header.get_last_hygiene_time")
    def test_due_today(self, mock_last):
        self._insert_item("shower", 7, due_today=1)
        # last log exactly 7 days ago
        mock_last.return_value = self._set_last_time("shower", 7)
        nudges = compute_hygiene_nudges(self.conn, relative_to=self.today_j)
        self.assertEqual(len(nudges), 1)
        self.assertIn("shower", nudges[0])
        self.assertIn("due today", nudges[0])

    @patch("dailydriver.features.hygiene._header.get_last_hygiene_time")
    def test_due_today_disabled(self, mock_last):
        self._insert_item("shower", 7, due_today=0)
        mock_last.return_value = self._set_last_time("shower", 7)
        nudges = compute_hygiene_nudges(self.conn, relative_to=self.today_j)
        self.assertEqual(nudges, [])

    @patch("dailydriver.features.hygiene._header.get_last_hygiene_time")
    def test_early_warning(self, mock_last):
        self._insert_item("shower", 7, early=1)
        # last log 6 days ago → 1 day remaining → within 2 days
        mock_last.return_value = self._set_last_time("shower", 6)
        nudges = compute_hygiene_nudges(self.conn, relative_to=self.today_j)
        self.assertEqual(len(nudges), 1)
        self.assertIn("shower", nudges[0])
        self.assertIn("due in 1d", nudges[0])

    @patch("dailydriver.features.hygiene._header.get_last_hygiene_time")
    def test_early_warning_disabled(self, mock_last):
        self._insert_item("shower", 7, early=0)
        mock_last.return_value = self._set_last_time("shower", 6)
        nudges = compute_hygiene_nudges(self.conn, relative_to=self.today_j)
        self.assertEqual(nudges, [])

    @patch("dailydriver.features.hygiene._header.get_last_hygiene_time")
    def test_no_nudge_well_within_interval(self, mock_last):
        self._insert_item("shower", 7, early=1)
        # last log 5 days ago → 2 days remaining, threshold is 2 days for interval 7
        # 2 remaining is NOT less than or equal to 2? Actually early_threshold = 2, remaining = 2
        # The code checks if remaining <= early_threshold: that would trigger. So 5 days ago → remaining = 2 → nudge.
        # Let's use 4 days ago → remaining = 3 > 2 → no nudge.
        mock_last.return_value = self._set_last_time("shower", 4)
        nudges = compute_hygiene_nudges(self.conn, relative_to=self.today_j)
        self.assertEqual(nudges, [])

    @patch("dailydriver.features.hygiene._header.get_last_hygiene_time")
    def test_interval_15_early_3_days(self, mock_last):
        self._insert_item("shave", 15, early=1)
        # last log 13 days ago → remaining = 2, threshold = 3 → due in 2d
        mock_last.return_value = self._set_last_time("shave", 13)
        nudges = compute_hygiene_nudges(self.conn, relative_to=self.today_j)
        self.assertEqual(len(nudges), 1)
        self.assertIn("shave", nudges[0])
        self.assertIn("due in 2d", nudges[0])


if __name__ == "__main__":
    unittest.main()
