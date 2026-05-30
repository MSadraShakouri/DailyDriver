import unittest
from unittest.mock import patch

import jdatetime

from dailydriver.display.header.calendar import get_reminders_str


class TestReminders(unittest.TestCase):
    def setUp(self):
        self.target_date = jdatetime.date.today()

    @patch("dailydriver.display.header.calendar.get_events")
    @patch("dailydriver.display.header.calendar.get_upcoming_events")
    def test_today_with_reminders(self, mock_upcoming, mock_events):
        mock_events.return_value = [{"title": "dummy"}]  # non-empty to avoid early return
        mock_upcoming.return_value = [
            (
                self.target_date + jdatetime.timedelta(days=2),
                {"remind": True, "title_en": "Meeting"},
            )
        ]
        s = get_reminders_str(self.target_date, is_today=True)
        self.assertIn("Meeting", s)
        self.assertIn("🔔", s)

    def test_not_today_empty(self):
        self.assertEqual(get_reminders_str(self.target_date, is_today=False), "")
