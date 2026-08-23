# tests/header/test_calendar.py
import sqlite3
import unittest
from unittest.mock import patch

import jdatetime

from dailydriver.features import calendar
from dailydriver.features.calendar.header import get_calendar_lines
from dailydriver.features.registry import validate_header_sections


class TestCalendarLines(unittest.TestCase):
    def setUp(self):
        self.target_date = jdatetime.date.today()

    @patch("dailydriver.features.calendar.catalog.get_events")
    @patch("dailydriver.features.calendar.catalog.get_todays_events")
    def test_today_events(self, mock_todays, mock_events):
        mock_todays.return_value = [{"calendar": "jalali", "holiday": False, "title_en": "Test Day"}]
        mock_events.return_value = []
        lines = get_calendar_lines(self.target_date, is_today=True)
        self.assertEqual(len(lines), 1)
        prefix, title = lines[0]
        self.assertIn("🔆", prefix)
        self.assertIn("Test Day", title)

    @patch("dailydriver.features.calendar.catalog.get_events_for_date")
    def test_past_events(self, mock_get_for_date):
        mock_get_for_date.return_value = [{"calendar": "gregorian", "holiday": True, "title_en": "Christmas"}]
        lines = get_calendar_lines(self.target_date, is_today=False)
        self.assertEqual(len(lines), 1)
        prefix, title = lines[0]
        self.assertIn("🌐", prefix)
        self.assertIn("🎊", prefix)
        self.assertIn("Christmas", title)

    @patch("dailydriver.features.calendar.catalog.get_events")
    def test_feature_hook_wraps_structured_calendar_line(self, mock_events):
        """A real calendar event satisfies the package-level header contract."""
        event = {
            "id": 1,
            "calendar": "jalali",
            "holiday": False,
            "title_en": "Test Day",
        }
        mock_events.return_value = [(self.target_date, event)]
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute("CREATE TABLE event_reminders (event_id INTEGER PRIMARY KEY, level INTEGER NOT NULL DEFAULT 0)")
        try:
            sections = calendar.header_sections(
                conn,
                self.target_date.strftime("%Y-%m-%d"),
                self.target_date,
                True,
            )
            assert (46, ("🔆 ", "Test Day")) in sections
            assert validate_header_sections(calendar, sections) == sections
        finally:
            conn.close()
