# tests/test_qada_header.py
import sqlite3
import unittest
from datetime import datetime
from unittest.mock import patch

import jdatetime

from dailydriver.features.qada.header import get_prayer_nudges
from dailydriver.features.qada.migrations import migrations


class TestQadaHeaderNudges(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)
        self.today = jdatetime.date.today()
        self.conn.execute(
            "INSERT INTO qada_entries (name, kind, interval_type, slot, target_total, logged_total) VALUES ('fajr', 'prayer', 'daily', 'fajr', 1, 0)"
        )
        self.conn.commit()
        self.entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE name='fajr'").fetchone())

    def tearDown(self):
        self.conn.close()

    @patch("dailydriver.features.qada.header.list_entries")
    @patch("dailydriver.features.qada.header.get_current_pending_instance")
    @patch("dailydriver.features.qada.header.get_approximate_times")
    def test_no_nudge_before_window_opens(self, mock_times, mock_pending, mock_list):
        mock_list.return_value = [self.entry]
        mock_pending.return_value = self.today
        mock_times.return_value = {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)}
        old_now = datetime.now().replace(hour=2, minute=0, second=0)
        nudges = get_prayer_nudges(self.conn, self.today, now=old_now)
        self.assertEqual(nudges, [])

    @patch("dailydriver.features.qada.header.list_entries")
    @patch("dailydriver.features.qada.header.get_current_pending_instance")
    @patch("dailydriver.features.qada.header.get_approximate_times")
    def test_nudge_appears_one_hour_before_prayer(self, mock_times, mock_pending, mock_list):
        mock_list.return_value = [self.entry]
        mock_pending.return_value = self.today
        mock_times.return_value = {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)}
        now = datetime.now().replace(hour=4, minute=1, second=0)
        nudges = get_prayer_nudges(self.conn, self.today, now=now)
        self.assertTrue(len(nudges) > 0)
        self.assertIn("🕌 Fajr pending", nudges[0])

    @patch("dailydriver.features.qada.header.list_entries")
    @patch("dailydriver.features.qada.header.get_current_pending_instance")
    @patch("dailydriver.features.qada.header.get_approximate_times")
    def test_logged_entry_no_longer_nudges(self, mock_times, mock_pending, mock_list):
        mock_list.return_value = [self.entry]
        mock_times.return_value = {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)}
        mock_pending.return_value = None
        now = datetime.now().replace(hour=6, minute=0, second=0)
        nudges = get_prayer_nudges(self.conn, self.today, now=now)
        self.assertEqual(nudges, [])

    @patch("dailydriver.features.qada.header.list_entries")
    @patch("dailydriver.features.qada.header.get_current_pending_instance")
    @patch("dailydriver.features.qada.header.get_approximate_times")
    def test_paused_entry_no_nudge(self, mock_times, mock_pending, mock_list):
        mock_list.return_value = [self.entry]
        mock_times.return_value = {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)}
        mock_pending.return_value = None
        now = datetime.now().replace(hour=6, minute=0, second=0)
        nudges = get_prayer_nudges(self.conn, self.today, now=now)
        self.assertEqual(nudges, [])

    @patch("dailydriver.features.qada.header.list_entries")
    @patch("dailydriver.features.qada.header.get_current_pending_instance")
    @patch("dailydriver.features.qada.header.get_approximate_times")
    def test_overdue_entry_shows_always(self, mock_times, mock_pending, mock_list):
        mock_list.return_value = [self.entry]
        mock_times.return_value = {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)}
        yesterday = self.today - jdatetime.timedelta(days=1)
        mock_pending.return_value = yesterday
        now = datetime.now().replace(hour=10, minute=0, second=0)
        nudges = get_prayer_nudges(self.conn, self.today, now=now)
        self.assertEqual(len(nudges), 1)
        self.assertIn("overdue", nudges[0])
