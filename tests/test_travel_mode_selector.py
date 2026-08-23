"""Test the prayer slot selector in travel mode."""

import sqlite3
import unittest
from datetime import datetime
from unittest.mock import patch

import jdatetime

from dailydriver.core import travel_mode
from dailydriver.features.prayer import commands


class TestTravelModeSelector(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

        # Create meta table (needed for travel mode)
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")

        # Create prayer_logs table with full schema (matching real table)
        self.conn.execute("""
            CREATE TABLE prayer_logs (
                id INTEGER PRIMARY KEY,
                prayer_slot TEXT,
                jalali_date TEXT,
                prayer_time INTEGER,
                status TEXT,
                logged_at INTEGER,
                jamaat_location TEXT,
                shak_count INTEGER
            )
        """)

        # Patch BOTH modules that use get_connection_cm
        self.patcher1 = patch("dailydriver.features.prayer.commands.get_connection_cm")
        self.patcher2 = patch("dailydriver.core.travel_mode.get_connection_cm")

        self.mock_cm1 = self.patcher1.start()
        self.mock_cm2 = self.patcher2.start()

        # Both use our test connection
        self.mock_cm1.return_value.__enter__.return_value = self.conn
        self.mock_cm2.return_value.__enter__.return_value = self.conn

        self.ui_patcher = patch("dailydriver.features.prayer.commands.current_ui")
        self.mock_ui = self.ui_patcher.start()

        # Enable travel mode (now works because both modules use the same connection)
        travel_mode.set_travel_mode(True)
        self.assertTrue(travel_mode.is_travel_mode(), "Travel mode should be enabled")

        self.today = jdatetime.date.today().strftime("%Y-%m-%d")

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.ui_patcher.stop()
        self.conn.close()

    def test_selector_shows_menu(self):
        self.mock_ui.confirm.return_value = True
        self.mock_ui.prompt.return_value = ""

        commands.log_prayer("p")

        self.mock_ui.print_line.assert_any_call("\nTravel mode: select prayer slot")
        self.mock_ui.print_line.assert_any_call("  [1] Fajr (suggested)")
        self.mock_ui.print_line.assert_any_call("  [2] Dhuhr & Asr")
        self.mock_ui.print_line.assert_any_call("  [3] Maghrib & Isha")
        self.mock_ui.print_line.assert_any_call("  [n] Cancel")

    def test_enter_accepts_default(self):
        self.mock_ui.confirm.return_value = True
        self.mock_ui.prompt.return_value = ""

        commands.log_prayer("p")

        cur = self.conn.cursor()
        cur.execute("SELECT prayer_slot FROM prayer_logs")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertIn(row["prayer_slot"], ("fajr", "dhuhr_asr", "maghrib_isha"))

    def test_1_selects_fajr(self):
        self.mock_ui.confirm.return_value = True
        self.mock_ui.prompt.return_value = "1"

        commands.log_prayer("p")

        cur = self.conn.cursor()
        cur.execute("SELECT prayer_slot FROM prayer_logs")
        row = cur.fetchone()
        self.assertEqual(row["prayer_slot"], "fajr")

    def test_2_selects_dhuhr(self):
        self.mock_ui.confirm.return_value = True
        self.mock_ui.prompt.return_value = "2"

        commands.log_prayer("p")

        cur = self.conn.cursor()
        cur.execute("SELECT prayer_slot FROM prayer_logs")
        row = cur.fetchone()
        self.assertEqual(row["prayer_slot"], "dhuhr_asr")

    def test_3_selects_maghrib(self):
        self.mock_ui.confirm.return_value = True
        self.mock_ui.prompt.return_value = "3"

        commands.log_prayer("p")

        cur = self.conn.cursor()
        cur.execute("SELECT prayer_slot FROM prayer_logs")
        row = cur.fetchone()
        self.assertEqual(row["prayer_slot"], "maghrib_isha")

    def test_n_cancels(self):
        self.mock_ui.prompt.return_value = "n"

        result = commands.log_prayer("p")
        self.assertIsNone(result)

        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(*) FROM prayer_logs")
        count = cur.fetchone()[0]
        self.assertEqual(count, 0)

    def test_explicit_time_no_selector(self):
        """With explicit time, travel mode still shows selector (just for slot)."""
        self.mock_ui.confirm.return_value = True
        self.mock_ui.prompt.return_value = "2"  # Select Dhuhr

        commands.log_prayer("p 14:30")

        # Menu should be shown (for slot selection)
        self.mock_ui.print_line.assert_any_call("\nTravel mode: select prayer slot")

        # Should log at the explicit time
        cur = self.conn.cursor()
        cur.execute("SELECT prayer_time, prayer_slot FROM prayer_logs")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        prayer_dt = datetime.fromtimestamp(row["prayer_time"])
        self.assertEqual(prayer_dt.strftime("%H:%M"), "14:30")
        self.assertEqual(row["prayer_slot"], "dhuhr_asr")

    def test_offset_no_selector(self):
        """With offset, travel mode still shows selector (just for slot)."""
        self.mock_ui.confirm.return_value = True
        self.mock_ui.prompt.return_value = "3"  # Select Maghrib

        commands.log_prayer("p -30")

        # Menu should be shown (for slot selection)
        self.mock_ui.print_line.assert_any_call("\nTravel mode: select prayer slot")

        # Should log at offset time
        cur = self.conn.cursor()
        cur.execute("SELECT prayer_time, prayer_slot FROM prayer_logs")
        row = cur.fetchone()
        self.assertIsNotNone(row)

        # Check that prayer_time is about 30 minutes ago (within a minute)
        now_ts = int(datetime.now().timestamp())
        prayer_ts = row["prayer_time"]
        self.assertAlmostEqual(now_ts - prayer_ts, 1800, delta=60)
        self.assertEqual(row["prayer_slot"], "maghrib_isha")
