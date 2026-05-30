# tests/test_reminder_system.py
import sqlite3
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import jdatetime

from dailydriver.features.birthdays._header import BIRTHDAY_SCHEDULE, get_birthday_lines
from dailydriver.utils.event_reminders import get_event_reminders, get_tomorrow_preview


class TestBirthdaySchedule(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE birthdays ("
            " id INTEGER PRIMARY KEY, name TEXT, month INTEGER, day INTEGER,"
            " year INTEGER, remind_level INTEGER DEFAULT 0"
            ")"
        )
        self.conn.commit()
        # Fixed target date: 26 Ordibehesht 1405 (Gregorian 2026-05-16)
        self.target = jdatetime.date(1405, 2, 26)

    def tearDown(self):
        self.conn.close()

    def test_level_0_at_14_days(self):
        """Birthday 14 days away (9 Khordad) with level 0 should appear."""
        self.conn.execute("INSERT INTO birthdays (name, month, day, year, remind_level) VALUES ('Test', 3, 9, 1380, 0)")
        # 25 Ord → 9 Khordad = 14 days
        lines = get_birthday_lines(self.conn, self.target)
        self.assertTrue(any("Test" in line for line in lines), "Birthday at 14d should be shown")

    def test_level_1_at_28_days(self):
        """Birthday 28 days away (23 Khordad) with level 1 should appear."""
        self.conn.execute("INSERT INTO birthdays (name, month, day, year, remind_level) VALUES ('VIP', 3, 23, 1370, 1)")
        # 25 Ord → 23 Khordad = 28 days
        lines = get_birthday_lines(self.conn, self.target)
        self.assertTrue(any("VIP" in line for line in lines), "VIP birthday at 28d should be shown")

    def test_not_shown_outside_schedule(self):
        """A birthday not matching the schedule should not appear."""
        self.conn.execute("INSERT INTO birthdays (name, month, day, year, remind_level) VALUES ('Far', 4, 1, 1390, 0)")
        # 25 Ord → 1 Tir is far, shouldn't appear
        lines = get_birthday_lines(self.conn, self.target)
        self.assertFalse(any("Far" in line for line in lines), "Far away birthday should not appear")


class TestEventReminders(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE event_reminders (event_id INTEGER PRIMARY KEY, level INTEGER NOT NULL DEFAULT 0)"
        )
        self.conn.commit()
        self.today = jdatetime.date.today()

    def tearDown(self):
        self.conn.close()

    def test_returns_reminder_line(self):
        self.conn.execute("INSERT INTO event_reminders (event_id, level) VALUES (1, 1)")
        events = [
            (
                self.today,
                {
                    "id": 1,
                    "title_en": "Test Event",
                    "calendar": "jalali",
                    "holiday": False,
                },
            )
        ]
        lines = get_event_reminders(self.conn, events, self.today)
        self.assertEqual(len(lines), 1)
        prefix, title = lines[0]
        self.assertIn("🔔", prefix)
        self.assertIn("Test Event (today)", title)

    def test_no_reminder_if_not_in_schedule(self):
        self.conn.execute("INSERT INTO event_reminders (event_id, level) VALUES (2, 1)")
        future_date = self.today + jdatetime.timedelta(days=5)  # not in [14,7,3,2,1,0]
        events = [
            (
                future_date,
                {
                    "id": 2,
                    "title_en": "Future",
                    "calendar": "gregorian",
                    "holiday": True,
                },
            )
        ]
        lines = get_event_reminders(self.conn, events, self.today)
        self.assertEqual(len(lines), 0)

    def test_holiday_alignment(self):
        self.conn.execute("INSERT INTO event_reminders (event_id, level) VALUES (1, 1)")
        self.conn.execute("INSERT INTO event_reminders (event_id, level) VALUES (2, 1)")
        events = [
            (
                self.today,
                {"id": 1, "title_en": "Holiday", "calendar": "jalali", "holiday": True},
            ),
            (
                self.today,
                {"id": 2, "title_en": "Normal", "calendar": "jalali", "holiday": False},
            ),
        ]
        lines = get_event_reminders(self.conn, events, self.today)
        # Normal event should have extra spaces for alignment
        normal_prefix = [p for p, t in lines if "Normal" in t][0]
        self.assertIn("  ", normal_prefix)  # two spaces for alignment


class TestTomorrowPreview(unittest.TestCase):
    def setUp(self):
        self.today = jdatetime.date.today()

    def test_excludes_reminded_events(self):
        reminded = {1}
        events = [
            (
                self.today + jdatetime.timedelta(days=1),
                {
                    "id": 1,
                    "title_en": "Reminded",
                    "calendar": "jalali",
                    "holiday": False,
                },
            ),
            (
                self.today + jdatetime.timedelta(days=1),
                {"id": 2, "title_en": "Normal", "calendar": "jalali", "holiday": False},
            ),
        ]
        lines = get_tomorrow_preview(events, self.today, reminded_ids=reminded)
        # First line is header, rest are tuples
        self.assertGreaterEqual(len(lines), 2)  # header + Normal event
        titles = [t if isinstance(t, str) else t[1] for t in lines]
        self.assertIn("Normal", titles)
        self.assertNotIn("Reminded", titles)

    def test_returns_empty_if_no_events(self):
        lines = get_tomorrow_preview([], self.today)
        self.assertEqual(lines, [])

    def test_returns_empty_if_only_reminded(self):
        reminded = {1}
        events = [
            (
                self.today + jdatetime.timedelta(days=1),
                {"id": 1, "title_en": "Only", "calendar": "jalali", "holiday": False},
            ),
        ]
        lines = get_tomorrow_preview(events, self.today, reminded_ids=reminded)
        self.assertEqual(lines, [])
