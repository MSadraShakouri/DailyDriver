# tests/header/test_calendar.py
import unittest
from unittest.mock import patch

import jdatetime

from dailydriver.display.header.calendar import get_calendar_lines


class TestCalendarLines(unittest.TestCase):
    def setUp(self):
        self.target_date = jdatetime.date.today()

    @patch("dailydriver.display.header.calendar.get_events")
    @patch("dailydriver.display.header.calendar.get_todays_events")
    def test_today_events(self, mock_todays, mock_events):
        mock_todays.return_value = [{"calendar": "jalali", "holiday": False, "title_en": "Test Day"}]
        mock_events.return_value = []
        lines = get_calendar_lines(self.target_date, is_today=True)
        self.assertEqual(len(lines), 1)
        prefix, title = lines[0]
        self.assertIn("🔆", prefix)
        self.assertIn("Test Day", title)

    @patch("dailydriver.display.header.calendar.get_events_for_date")
    def test_past_events(self, mock_get_for_date):
        mock_get_for_date.return_value = [{"calendar": "gregorian", "holiday": True, "title_en": "Christmas"}]
        lines = get_calendar_lines(self.target_date, is_today=False)
        self.assertEqual(len(lines), 1)
        prefix, title = lines[0]
        self.assertIn("🌐", prefix)
        self.assertIn("🎊", prefix)
        self.assertIn("Christmas", title)
