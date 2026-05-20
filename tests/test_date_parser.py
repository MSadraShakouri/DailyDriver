# tests/test_date_parser.py
import unittest
from datetime import datetime
from dailydriver.core.date_parser import _parse_relative_date


class TestRelativeDateParser(unittest.TestCase):
    def setUp(self):
        # Fixed "now": Wednesday, 20 May 2026, 14:30
        self.now = datetime(2026, 5, 20, 14, 30, 0)

    def test_yesterday(self):
        result = _parse_relative_date("yesterday", self.now)
        self.assertEqual(result, datetime(2026, 5, 19, 0, 0, 0))

    def test_today(self):
        result = _parse_relative_date("today", self.now)
        self.assertEqual(result, datetime(2026, 5, 20, 0, 0, 0))

    def test_tomorrow(self):
        result = _parse_relative_date("tomorrow", self.now)
        self.assertEqual(result, datetime(2026, 5, 21, 0, 0, 0))

    def test_last_monday(self):
        result = _parse_relative_date("last Monday", self.now)
        # Monday is 0, Wednesday is 2: (2-0)%7 = 2, but "last Monday" is the one before this week.
        # The code: days_ago = (now.weekday() - wd) % 7; if 0: days_ago = 7
        # For Monday (0): days_ago = (2 - 0)%7 = 2 -> 2026-05-18
        self.assertEqual(result, datetime(2026, 5, 18, 0, 0, 0))

    def test_last_wednesday(self):
        result = _parse_relative_date("last Wednesday", self.now)
        # Wednesday (2): days_ago = (2-2)%7 = 0 -> 7 -> 2026-05-13
        self.assertEqual(result, datetime(2026, 5, 13, 0, 0, 0))

    def test_next_monday(self):
        result = _parse_relative_date("next Monday", self.now)
        # Monday (0): days_ahead = (0-2)%7 = 5 -> 2026-05-25
        self.assertEqual(result, datetime(2026, 5, 25, 0, 0, 0))

    def test_plain_monday(self):
        result = _parse_relative_date("Monday", self.now)
        # Plain weekday = nearest past: (2-0)%7 = 2 -> 2026-05-18
        self.assertEqual(result, datetime(2026, 5, 18, 0, 0, 0))

    def test_plain_wednesday(self):
        result = _parse_relative_date("Wednesday", self.now)
        # (2-2)%7 = 0 -> 7 -> 2026-05-13
        self.assertEqual(result, datetime(2026, 5, 13, 0, 0, 0))

    def test_3_days_ago(self):
        result = _parse_relative_date("3 days ago", self.now)
        self.assertEqual(result, datetime(2026, 5, 17, 0, 0, 0))

    def test_in_4_days(self):
        result = _parse_relative_date("in 4 days", self.now)
        self.assertEqual(result, datetime(2026, 5, 24, 0, 0, 0))

    def test_unknown_text(self):
        result = _parse_relative_date("some random text", self.now)
        self.assertIsNone(result)

    def test_empty_text(self):
        result = _parse_relative_date("", self.now)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
