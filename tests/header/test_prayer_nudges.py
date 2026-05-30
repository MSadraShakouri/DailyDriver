import sqlite3
import unittest
from datetime import datetime

import jdatetime

from dailydriver.display.header.prayer import get_prayer_nudges


class TestPrayerNudges(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE prayer_logs (id INTEGER PRIMARY KEY, prayer_slot TEXT, jalali_date TEXT, prayer_time INTEGER, status TEXT)"
        )
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        self.today_str = "1405-02-21"
        self.target_date = jdatetime.date(1405, 2, 21)

    def tearDown(self):
        self.conn.close()

    def test_overdue_today(self):
        # Fixed "now": after maghrib on this date
        fixed_now = datetime(2026, 5, 11, 20, 0, 0)
        nudges = get_prayer_nudges(self.conn, self.target_date, self.today_str, is_today=True, now=fixed_now)
        self.assertTrue(any("Maghrib" in n and "not logged" in n for n in nudges))

    def test_no_nudges_when_not_today(self):
        nudges = get_prayer_nudges(self.conn, self.target_date, self.today_str, is_today=False)
        self.assertEqual(nudges, [])
