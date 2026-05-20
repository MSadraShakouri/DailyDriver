import sqlite3
import unittest
from datetime import datetime

from dailydriver.display.header.prayer import get_prayer_parts


class TestPrayerParts(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""CREATE TABLE prayer_logs (
            id INTEGER PRIMARY KEY, prayer_slot TEXT, jalali_date TEXT,
            prayer_time INTEGER, status TEXT, logged_at INTEGER,
            jamaat_location TEXT, shak_count INTEGER)""")
        self.today = "1405-02-21"

    def tearDown(self):
        self.conn.close()

    def test_no_logs_all_dashes(self):
        parts = get_prayer_parts(self.conn, self.today)
        self.assertEqual(len(parts), 3)
        for p in parts:
            self.assertIn("—", p)

    def test_fajr_logged_shows_time(self):
        self.conn.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, prayer_time) VALUES (?,?,?)",
            ("fajr", self.today, int(datetime(2026, 5, 9, 4, 42, 0).timestamp())),
        )
        parts = get_prayer_parts(self.conn, self.today)
        self.assertIn("04:42", parts[0])
