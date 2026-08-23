"""Test that travel mode disables location-dependent features."""

import sqlite3
import unittest
from unittest.mock import patch

import jdatetime

from dailydriver.core.state import set_travel_mode


class TestTravelModeDisabled(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        self.conn.execute(
            """
            CREATE TABLE prayer_logs (
                id INTEGER PRIMARY KEY,
                prayer_slot TEXT,
                jalali_date TEXT,
                prayer_time INTEGER,
                status TEXT,
                logged_at INTEGER
            )
            """
        )
        self.today = jdatetime.date.today().strftime("%Y-%m-%d")

        self.patcher = patch("dailydriver.core.state.meta.get_connection_cm")
        self.mock_cm = self.patcher.start()
        self.mock_cm.return_value.__enter__.return_value = self.conn
        self.mock_cm.return_value.__exit__.return_value = False

    def tearDown(self):
        self.patcher.stop()
        self.conn.close()

    def test_weather_shows_travel_mode_instead_of_weather(self):
        set_travel_mode(True)
        from dailydriver.features.weather.header import get_weather_str

        result = get_weather_str(self.conn, self.today, is_today=True)
        self.assertEqual(result, "🌍 Travel mode")

    def test_weather_shows_weather_when_disabled(self):
        set_travel_mode(False)
        with patch("dailydriver.features.weather.header.get_weather") as mock_weather:
            mock_weather.return_value = {"temp_c": 28, "condition_en": "clear", "condition_emoji": "☀️", "timestamp": 0}
            from dailydriver.features.weather.header import get_weather_str

            result = get_weather_str(self.conn, self.today, is_today=True)
            self.assertIn("28°C", result)
            mock_weather.assert_called_once()

    def test_prayer_nudges_disabled(self):
        set_travel_mode(True)
        from dailydriver.features.prayer.nudges import get_prayer_nudges

        result = get_prayer_nudges(self.conn, jdatetime.date.today(), self.today, is_today=True)
        expected = ["\x1b[31m⚠️ Fajr not logged (today)\x1b[0m"]
        self.assertEqual(result, expected)

    def test_qada_nudges_disabled(self):
        set_travel_mode(True)
        from dailydriver.features.qada.header import get_prayer_nudges

        result = get_prayer_nudges(self.conn, jdatetime.date.today())
        self.assertEqual(result, [])
