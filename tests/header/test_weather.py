import sqlite3
import time
import unittest
from datetime import datetime
from unittest.mock import patch

import jdatetime

from dailydriver.display.header.weather import get_weather_str


class TestWeather(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE weather_log (id INTEGER PRIMARY KEY, temp_c INTEGER, condition_fa TEXT, timestamp INTEGER)"
        )
        self.today = "1405-02-21"

    def tearDown(self):
        self.conn.close()

    @patch("dailydriver.display.header.weather.get_weather")
    def test_live_today(self, mock_get_weather):
        mock_get_weather.return_value = {
            "temp_c": 30,
            "condition_en": "clear",
            "condition_emoji": "☀️",
            "timestamp": time.time(),
        }
        s = get_weather_str(self.conn, self.today, is_today=True)
        self.assertIn("30°C", s)
        self.assertIn("clear", s)

    def test_cached_past(self):
        y, m, d = map(int, self.today.split("-"))
        gdate = jdatetime.date(y, m, d).togregorian()
        ts = int(datetime(gdate.year, gdate.month, gdate.day, 12, 0, 0).timestamp())
        self.conn.execute(
            "INSERT INTO weather_log (temp_c, condition_fa, timestamp) VALUES (?,?,?)",
            (25, "صاف", ts),
        )
        s = get_weather_str(self.conn, self.today, is_today=False)
        self.assertIn("25°C", s)
