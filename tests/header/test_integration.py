import sqlite3
import unittest
from unittest.mock import patch

from dailydriver.display.header import build_header_data


class TestIntegration(unittest.TestCase):
    def test_build_header_data_structure(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE prayer_logs (id INTEGER PRIMARY KEY, prayer_slot TEXT, jalali_date TEXT, prayer_time INTEGER);
            CREATE TABLE sleep_logs (id INTEGER PRIMARY KEY, jalali_date TEXT, sleep_time INTEGER, wake_time INTEGER, duration_minutes INTEGER);
            CREATE TABLE nap_logs (id INTEGER PRIMARY KEY, jalali_date TEXT, start_time INTEGER, duration_minutes INTEGER);
            CREATE TABLE birthdays (id INTEGER PRIMARY KEY, name TEXT, month INTEGER, day INTEGER, year INTEGER, remind_level INTEGER DEFAULT 0);
            CREATE TABLE hygiene_config (id INTEGER PRIMARY KEY, item TEXT, desired_interval_days INTEGER, early_warning_enabled INTEGER, show_due_today INTEGER);
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE weather_log (id INTEGER PRIMARY KEY, temp_c INTEGER, condition_fa TEXT, timestamp INTEGER);
            CREATE TABLE event_reminders (event_id INTEGER PRIMARY KEY, level INTEGER NOT NULL DEFAULT 0);
        """)
        cur.execute("INSERT INTO meta (key, value) VALUES ('prayer_complete_until', '1405-02-20')")
        conn.commit()

        with patch("dailydriver.display.header.get_connection_cm") as mock_cm:
            mock_cm.return_value.__enter__.return_value = conn
            with (
                patch(
                    "dailydriver.features.events.header.get_active_great_event",
                    return_value=None,
                ),
                patch(
                    "dailydriver.features.events.header.get_pending_start",
                    return_value=None,
                ),
                patch("dailydriver.features.calendar.catalog.get_events", return_value=[]),
                patch("dailydriver.features.calendar.catalog.get_todays_events", return_value=[]),
                patch("dailydriver.features.calendar.catalog.get_upcoming_events", return_value=[]),
                patch(
                    "dailydriver.features.weather.header.get_weather",
                    return_value=None,
                ),
                patch(
                    "dailydriver.features.qada.header.get_prayer_nudges",
                    return_value=[],
                ),
                patch(
                    "dailydriver.features.targets.header.header_sections",
                    return_value=[],
                ),
            ):
                data = build_header_data(day=None, is_today=True)

        expected_keys = [
            "jalali_line",
            "separator",
            "greg_hijri_line",
            "feature_lines",
            "is_today",
        ]
        for key in expected_keys:
            self.assertIn(key, data)
        self.assertTrue(data["is_today"])
        conn.close()
