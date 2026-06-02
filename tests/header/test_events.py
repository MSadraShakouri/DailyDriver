import time
import unittest
from unittest.mock import patch

from dailydriver.features.events._header import (
    get_great_event_str,
    get_last_entry_time,
    get_running_event_str,
)


class TestEvents(unittest.TestCase):
    @patch("dailydriver.features.events._header.get_active_great_event")
    def test_great_event_today(self, mock_ge):
        mock_ge.return_value = (int(time.time()) - 3600, ["work"])
        s = get_great_event_str(is_today=True)
        self.assertIn("Great Event", s)

    def test_great_event_not_today(self):
        self.assertEqual(get_great_event_str(is_today=False), "")

    @patch("dailydriver.features.events._header.get_pending_start")
    def test_running_event_today(self, mock_ps):
        mock_ps.return_value = int(time.time()) - 600
        s = get_running_event_str(is_today=True)
        self.assertIn("Event running since", s)

    def test_running_event_not_today(self):
        self.assertEqual(get_running_event_str(is_today=False), "")

    @patch("dailydriver.features.events._header.get_last_action_time")
    def test_last_entry_today(self, mock_la):
        mock_la.return_value = int(time.time()) - 120
        s = get_last_entry_time(is_today=True)
        self.assertRegex(s, r"\d{2}:\d{2}")

    def test_last_entry_not_today(self):
        self.assertEqual(get_last_entry_time(is_today=False), "")
