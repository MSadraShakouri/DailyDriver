"""Test that travel mode disables location-dependent features."""

import sqlite3
import unittest
from unittest.mock import patch

import jdatetime

from dailydriver.core import travel_mode


class TestTravelModeDisabled(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        
        # Create meta table (needed for travel mode)
        self.conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        
        # Also create prayer_logs table (needed for prayer nudges)
        self.conn.execute("""
            CREATE TABLE prayer_logs (
                id INTEGER PRIMARY KEY,
                prayer_slot TEXT,
                jalali_date TEXT,
                prayer_time INTEGER,
                status TEXT,
                logged_at INTEGER
            )
        """)
        
        self.today = jdatetime.date.today().strftime("%Y-%m-%d")

        self.patcher = patch("dailydriver.core.travel_mode.get_connection_cm")
        self.mock_cm = self.patcher.start()
        self.mock_cm.return_value.__enter__.return_value = self.conn
        self.mock_cm.return_value.__exit__.return_value = False

    def tearDown(self):
        self.patcher.stop()
        self.conn.close()

    def test_weather_shows_travel_mode_instead_of_weather(self):
        travel_mode.set_travel_mode(True)
        from dailydriver.features.weather._header import get_weather_str
        result = get_weather_str(self.conn, self.today, is_today=True)
        self.assertEqual(result, "🌍 Travel mode")

    def test_weather_shows_weather_when_disabled(self):
        travel_mode.set_travel_mode(False)
        with patch("dailydriver.features.weather._header.get_weather") as mock_weather:
            mock_weather.return_value = {"temp_c": 28, "condition_en": "clear", "condition_emoji": "☀️", "timestamp": 0}
            from dailydriver.features.weather._header import get_weather_str
            result = get_weather_str(self.conn, self.today, is_today=True)
            self.assertIn("28°C", result)
            mock_weather.assert_called_once()

    def test_prayer_nudges_disabled(self):
        travel_mode.set_travel_mode(True)
        from dailydriver.features.prayer._header import get_prayer_nudges
        result = get_prayer_nudges(self.conn, jdatetime.date.today(), self.today, is_today=True)
        self.assertEqual(result, [])

    def test_qada_nudges_disabled(self):
        travel_mode.set_travel_mode(True)
        from dailydriver.features.qada._header import get_prayer_nudges
        result = get_prayer_nudges(self.conn, jdatetime.date.today())
        self.assertEqual(result, [])
