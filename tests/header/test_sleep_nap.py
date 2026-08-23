import sqlite3
import unittest
from datetime import datetime

from dailydriver.features.sleep.status import get_nap_str, get_sleep_str


class TestSleep(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE sleep_logs (id INTEGER PRIMARY KEY, jalali_date TEXT, sleep_time INTEGER, wake_time INTEGER, duration_minutes INTEGER)"
        )
        self.today = "1405-02-21"

    def tearDown(self):
        self.conn.close()

    def test_no_sleep(self):
        self.assertEqual(get_sleep_str(self.conn, self.today), "💤 —")

    def test_sleep_logged(self):
        sleep_ts = int(datetime(2026, 5, 8, 23, 0, 0).timestamp())
        wake_ts = int(datetime(2026, 5, 9, 7, 0, 0).timestamp())
        self.conn.execute(
            "INSERT INTO sleep_logs (jalali_date, sleep_time, wake_time, duration_minutes) VALUES (?,?,?,?)",
            (self.today, sleep_ts, wake_ts, 480),
        )
        s = get_sleep_str(self.conn, self.today)
        self.assertIn("8h 0m", s)
        self.assertIn("23:00", s)
        self.assertIn("07:00", s)


class TestNap(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE nap_logs (id INTEGER PRIMARY KEY, jalali_date TEXT, start_time INTEGER, duration_minutes INTEGER)"
        )
        self.today = "1405-02-21"

    def tearDown(self):
        self.conn.close()

    def test_no_naps(self):
        self.assertEqual(get_nap_str(self.conn, self.today), "")

    def test_naps_total(self):
        self.conn.execute(
            "INSERT INTO nap_logs (jalali_date, start_time, duration_minutes) VALUES (?,?,?)",
            (self.today, int(datetime(2026, 5, 9, 13, 0, 0).timestamp()), 20),
        )
        nap = get_nap_str(self.conn, self.today)
        self.assertIn("0h 20m", nap)
