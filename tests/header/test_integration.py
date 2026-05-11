import unittest
import sqlite3
from unittest.mock import patch
from dailydriver.display.header import build_header_data


class TestIntegration(unittest.TestCase):
    def test_build_header_data_structure(self):
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.executescript('''
            CREATE TABLE prayer_logs (id INTEGER PRIMARY KEY, prayer_slot TEXT, jalali_date TEXT, prayer_time INTEGER);
            CREATE TABLE sleep_logs (id INTEGER PRIMARY KEY, jalali_date TEXT, sleep_time INTEGER, wake_time INTEGER, duration_minutes INTEGER);
            CREATE TABLE nap_logs (id INTEGER PRIMARY KEY, jalali_date TEXT, start_time INTEGER, duration_minutes INTEGER);
            CREATE TABLE birthdays (id INTEGER PRIMARY KEY, name TEXT, month INTEGER, day INTEGER, year INTEGER);
            CREATE TABLE hygiene_config (id INTEGER PRIMARY KEY, item TEXT, desired_interval_days INTEGER, early_warning_enabled INTEGER, show_due_today INTEGER);
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
            CREATE TABLE weather_log (id INTEGER PRIMARY KEY, temp_c INTEGER, condition_fa TEXT, timestamp INTEGER);
        ''')
        cur.execute("INSERT INTO meta (key, value) VALUES ('prayer_complete_until', '1405-02-20')")
        conn.commit()

        with patch('dailydriver.display.header.get_connection_cm') as mock_cm:
            mock_cm.return_value.__enter__.return_value = conn
            with patch('dailydriver.display.header.events.get_active_great_event', return_value=None), \
                 patch('dailydriver.display.header.events.get_pending_start', return_value=None), \
                 patch('dailydriver.display.header.calendar.get_events', return_value=[]), \
                 patch('dailydriver.display.header.calendar.get_todays_events', return_value=[]), \
                 patch('dailydriver.display.header.calendar.get_upcoming_events', return_value=[]), \
                 patch('dailydriver.display.header.weather.get_weather', return_value=None):
                data = build_header_data(day=None, is_today=True)

        expected_keys = ['date_str', 'prayer_parts', 'sleep_str', 'nap_str', 'bday_str',
                         'hygiene_str', 'calendar_lines', 'reminders_str', 'event_str',
                         'great_event_str', 'last_entry_time', 'weather_str',
                         'prayer_nudges', 'is_today']
        for key in expected_keys:
            self.assertIn(key, data)
        self.assertTrue(data['is_today'])
        self.assertIsInstance(data['prayer_parts'], list)
        self.assertIsInstance(data['prayer_nudges'], list)
        conn.close()
