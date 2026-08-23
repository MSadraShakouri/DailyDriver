"""Tests for day_start_hour functionality."""

import sqlite3
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import jdatetime

from dailydriver.core import day_start
from dailydriver.core.migration import run_migrations


class TestDayStartCore(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

        # Manually create meta table (migrations might not run in test)
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")

        # Also create other tables that might be needed by migrations
        # But we just need meta for these tests

        # Patch get_connection_cm to use our in-memory connection
        self.patcher = patch("dailydriver.core.day_start.get_connection_cm")
        self.mock_cm = self.patcher.start()
        self.mock_cm.return_value.__enter__.return_value = self.conn
        self.mock_cm.return_value.__exit__.return_value = False

    def tearDown(self):
        self.patcher.stop()
        self.conn.close()

    def test_get_day_start_hour_default(self):
        """Default should be 4 if not set."""
        self.assertEqual(day_start.get_day_start_hour(), 4)

    def test_get_day_start_hour_from_meta(self):
        """Should read from meta table."""
        self.conn.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('day_start_hour', '6')")
        self.conn.commit()
        self.assertEqual(day_start.get_day_start_hour(), 6)

    def test_set_day_start_hour(self):
        """Should write to meta table."""
        day_start.set_day_start_hour(7)
        cur = self.conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key = 'day_start_hour'")
        row = cur.fetchone()
        self.assertEqual(row["value"], "7")

    def test_set_day_start_hour_invalid(self):
        """Should raise ValueError for invalid hours."""
        with self.assertRaises(ValueError):
            day_start.set_day_start_hour(-1)
        with self.assertRaises(ValueError):
            day_start.set_day_start_hour(24)

    def test_get_shifted_today_before_hour(self):
        """If now.hour < day_start_hour, return yesterday."""
        with patch("dailydriver.core.day_start.get_day_start_hour", return_value=6):
            now = datetime(2026, 7, 25, 5, 0, 0)  # 5:00 AM, before 6
            result = day_start.get_shifted_today(now)
            expected = jdatetime.date(1405, 5, 2)  # 2026-07-24 in Jalali
            self.assertEqual(result, expected)

    def test_get_shifted_today_after_hour(self):
        """If now.hour >= day_start_hour, return today."""
        with patch("dailydriver.core.day_start.get_day_start_hour", return_value=6):
            now = datetime(2026, 7, 25, 7, 0, 0)  # 7:00 AM, after 6
            result = day_start.get_shifted_today(now)
            expected = jdatetime.date(1405, 5, 3)  # 2026-07-25 in Jalali
            self.assertEqual(result, expected)

    def test_get_shifted_today_exact_hour(self):
        """If now.hour == day_start_hour, return today."""
        with patch("dailydriver.core.day_start.get_day_start_hour", return_value=6):
            now = datetime(2026, 7, 25, 6, 0, 0)
            result = day_start.get_shifted_today(now)
            expected = jdatetime.date(1405, 5, 3)
            self.assertEqual(result, expected)

    def test_get_shifted_today_default_hour(self):
        """Default hour 4 should work."""
        # Default is 4, so 3:00 AM is before
        now = datetime(2026, 7, 25, 3, 0, 0)
        result = day_start.get_shifted_today(now)
        expected = jdatetime.date(1405, 5, 2)
        self.assertEqual(result, expected)

        now = datetime(2026, 7, 25, 5, 0, 0)
        result = day_start.get_shifted_today(now)
        expected = jdatetime.date(1405, 5, 3)
        self.assertEqual(result, expected)


class TestDayStartCommand(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")

        # Patch the module that daystart_command imports from (day_start)
        self.patcher = patch("dailydriver.core.day_start.get_connection_cm")
        self.mock_cm = self.patcher.start()
        self.mock_cm.return_value.__enter__.return_value = self.conn
        self.mock_cm.return_value.__exit__.return_value = False

        from dailydriver.cli.commands import daystart as daystart_cmd

        self.cmd = daystart_cmd.daystart_command

    def tearDown(self):
        self.patcher.stop()
        self.conn.close()

    def test_command_show_default(self):
        result = self.cmd("daystart")
        self.assertEqual(result, "Day start: 04:00")

    def test_command_set(self):
        result = self.cmd("daystart 7")
        self.assertEqual(result, "Day start set to 07:00")

        cur = self.conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key = 'day_start_hour'")
        row = cur.fetchone()
        self.assertEqual(row["value"], "7")

    def test_command_invalid_hour(self):
        result = self.cmd("daystart 25")
        self.assertEqual(result, "Invalid hour: 25. Must be 0-23.")

    def test_command_not_number(self):
        result = self.cmd("daystart abc")
        self.assertEqual(result, "Invalid hour: abc. Must be 0-23.")

    def test_command_too_many_args(self):
        result = self.cmd("daystart 7 8")
        self.assertEqual(result, "Usage: daystart          → show current\n       daystart <0-23>   → set hour")


class TestDayStartHygieneIntegration(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

        # Create necessary tables
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        self.conn.execute("""
            CREATE TABLE hygiene_config (
                id INTEGER PRIMARY KEY,
                item TEXT UNIQUE,
                desired_interval_days INTEGER,
                early_warning_enabled INTEGER DEFAULT 1,
                show_due_today INTEGER DEFAULT 1
            )
        """)
        self.conn.execute("""
            CREATE TABLE entries (
                id INTEGER PRIMARY KEY,
                created_at INTEGER,
                started_at INTEGER,
                duration_minutes INTEGER,
                description TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE categories (id INTEGER PRIMARY KEY, path TEXT UNIQUE)
        """)
        self.conn.execute("""
            CREATE TABLE entry_categories (
                entry_id INTEGER,
                category_id INTEGER,
                PRIMARY KEY (entry_id, category_id)
            )
        """)
        self.conn.commit()

        # Patch get_connection_cm for hygiene modules
        self.patcher = patch("dailydriver.features.hygiene.manager.get_connection_cm")
        self.mock_cm = self.patcher.start()
        self.mock_cm.return_value.__enter__.return_value = self.conn
        self.mock_cm.return_value.__exit__.return_value = False

        # Patch get_shifted_today
        self.date_patcher = patch("dailydriver.features.hygiene.header.get_shifted_today")
        self.mock_shifted = self.date_patcher.start()

        # Insert a hygiene item
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO hygiene_config (item, desired_interval_days, early_warning_enabled, show_due_today) VALUES (?, ?, ?, ?)",
            ("shower", 2, 0, 1),
        )
        cur.execute("INSERT INTO categories (path) VALUES ('hygiene/shower')")
        self.conn.commit()

        # Set default day start to 0 so we don't get weird shifts
        day_start.set_day_start_hour(0)

    def tearDown(self):
        self.patcher.stop()
        self.date_patcher.stop()
        self.conn.close()

    def test_hygiene_compute_nudges_uses_shifted_today(self):
        """compute_hygiene_nudges should use the shifted date for relative_to."""
        # Mock shifted today to be 1405-05-03
        self.mock_shifted.return_value = jdatetime.date(1405, 5, 3)

        # Insert a log entry at 1405-05-02 (1 day ago)
        last_time = datetime(2026, 7, 24, 12, 0, 0).timestamp()
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO entries (created_at, started_at, description) VALUES (?, ?, ?)",
            (int(last_time), int(last_time), "shower"),
        )
        entry_id = cur.lastrowid
        cur.execute("SELECT id FROM categories WHERE path = 'hygiene/shower'")
        row = cur.fetchone()
        if row:
            cat_id = row["id"]
            cur.execute("INSERT INTO entry_categories (entry_id, category_id) VALUES (?, ?)", (entry_id, cat_id))
        self.conn.commit()

        from dailydriver.features.hygiene.header import compute_hygiene_nudges

        # With shifted today = 1405-05-03, last log = 1405-05-02 → days_since = 1
        # Interval = 2 → days_left = 1 → not due today
        nudges = compute_hygiene_nudges(self.conn, relative_to=self.mock_shifted.return_value)
        # Early warning is off, so no nudge
        self.assertEqual(len(nudges), 0)

        # Now shift today to 1405-05-04 → days_since = 2 → days_left = 0 → due today
        self.mock_shifted.return_value = jdatetime.date(1405, 5, 4)
        nudges = compute_hygiene_nudges(self.conn, relative_to=self.mock_shifted.return_value)
        self.assertEqual(len(nudges), 1)
        self.assertIn("due today", nudges[0])


class TestDayStartTargetsIntegration(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row

        # Create necessary tables
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        self.conn.execute("""
            CREATE TABLE target_entries (
                id INTEGER PRIMARY KEY,
                kind TEXT,
                name TEXT UNIQUE,
                target_total INTEGER,
                logged_total INTEGER DEFAULT 0,
                interval_type TEXT,
                interval_value INTEGER,
                target_per_interval INTEGER,
                paused_until TEXT,
                created_at INTEGER
            )
        """)
        self.conn.execute("""
            CREATE TABLE target_logs (
                id INTEGER PRIMARY KEY,
                entry_id INTEGER,
                amount INTEGER,
                instance_date TEXT,
                logged_at INTEGER
            )
        """)
        self.conn.commit()

        # Patch get_connection_cm for targets
        self.patcher = patch("dailydriver.features.targets.entries.get_connection_cm")
        self.mock_cm = self.patcher.start()
        self.mock_cm.return_value.__enter__.return_value = self.conn
        self.mock_cm.return_value.__exit__.return_value = False

        # Patch get_shifted_today
        self.date_patcher = patch("dailydriver.features.targets.clock.today")
        self.mock_shifted = self.date_patcher.start()

        # Set default day start to 0
        day_start.set_day_start_hour(0)

        from dailydriver.features.targets import api as targets_logic

        self.targets_logic = targets_logic

        # Insert a target entry
        self.entry_id = self.targets_logic.add_entry(
            kind="nazr",
            name="Salavat",
            target_total=100,
            interval_type="daily",
            interval_value=1,
            target_per_interval=10,
        )

    def tearDown(self):
        self.patcher.stop()
        self.date_patcher.stop()
        self.conn.close()

    def test_targets_log_progress_uses_shifted_today_for_instance_date(self):
        # Set shifted today to 1405-05-03
        self.mock_shifted.return_value = jdatetime.date(1405, 5, 3)

        self.targets_logic.log_progress("Salavat", 5)

        cur = self.conn.cursor()
        cur.execute("SELECT instance_date FROM target_logs WHERE entry_id = ?", (self.entry_id,))
        row = cur.fetchone()
        self.assertEqual(row["instance_date"], "1405-05-03")

    def test_targets_log_progress_uses_shifted_today_with_day_start(self):
        # Set shifted today to 1405-05-04
        self.mock_shifted.return_value = jdatetime.date(1405, 5, 4)

        self.targets_logic.log_progress("Salavat", 5)

        cur = self.conn.cursor()
        cur.execute(
            "SELECT instance_date FROM target_logs WHERE entry_id = ? ORDER BY id DESC LIMIT 1", (self.entry_id,)
        )
        row = cur.fetchone()
        self.assertEqual(row["instance_date"], "1405-05-04")


if __name__ == "__main__":
    unittest.main()
