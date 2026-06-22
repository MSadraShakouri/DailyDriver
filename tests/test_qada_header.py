# tests/test_qada_header.py
import sqlite3
import unittest
from datetime import datetime
from unittest.mock import patch

import jdatetime

from dailydriver.features.qada._header import get_prayer_nudges
from dailydriver.features.qada._migrations import migrations


class TestQadaHeaderNudges(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for mig in migrations():
            mig(self.conn)
        self.today = jdatetime.date.today()
        # Add a daily Fajr entry with slot set
        self.conn.execute(
            "INSERT INTO qada_entries (name, kind, interval_type, slot) VALUES ('fajr', 'prayer', 'daily', 'fajr')"
        )
        self.conn.commit()
        self.entry = dict(self.conn.execute("SELECT * FROM qada_entries WHERE name='fajr'").fetchone())

    def tearDown(self):
        self.conn.close()

    @patch("dailydriver.features.qada._header.list_entries")
    @patch("dailydriver.features.qada._header.compute_pending_instance")
    def test_no_nudge_before_window_opens(self, mock_compute, mock_list):
        mock_list.return_value = [self.entry]
        mock_compute.return_value = self.today  # pending today
        old_now = datetime.now().replace(hour=2, minute=0, second=0)
        nudges = get_prayer_nudges(self.conn, self.today, now=old_now)
        self.assertEqual(nudges, [])

    @patch("dailydriver.features.qada._header.list_entries")
    @patch("dailydriver.features.qada._header.compute_pending_instance")
    @patch("dailydriver.features.qada._header.get_approximate_times")
    def test_nudge_appears_one_hour_before_prayer(self, mock_times, mock_compute, mock_list):
        mock_list.return_value = [self.entry]
        mock_compute.return_value = self.today
        mock_times.return_value = {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)}
        now = datetime.now().replace(hour=4, minute=1, second=0)
        nudges = get_prayer_nudges(self.conn, self.today, now=now)
        self.assertTrue(len(nudges) > 0)
        self.assertIn("fajr qada pending", nudges[0])

    @patch("dailydriver.features.qada._header.list_entries")
    @patch("dailydriver.features.qada._header.compute_pending_instance")
    @patch("dailydriver.features.qada._header.get_approximate_times")
    def test_logged_entry_no_longer_nudges(self, mock_times, mock_compute, mock_list):
        mock_list.return_value = [self.entry]
        mock_times.return_value = {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)}
        # compute_pending_instance returns None → no pending instance → no nudge
        mock_compute.return_value = None
        now = datetime.now().replace(hour=6, minute=0, second=0)
        nudges = get_prayer_nudges(self.conn, self.today, now=now)
        self.assertEqual(nudges, [])

    @patch("dailydriver.features.qada._header.list_entries")
    @patch("dailydriver.features.qada._header.compute_pending_instance")
    @patch("dailydriver.features.qada._header.get_approximate_times")
    def test_paused_entry_no_nudge(self, mock_times, mock_compute, mock_list):
        mock_list.return_value = [self.entry]
        mock_times.return_value = {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)}
        # compute returns None → paused → no nudge
        mock_compute.return_value = None
        now = datetime.now().replace(hour=6, minute=0, second=0)
        nudges = get_prayer_nudges(self.conn, self.today, now=now)
        self.assertEqual(nudges, [])
