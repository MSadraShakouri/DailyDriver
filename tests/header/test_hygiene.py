import unittest
import sqlite3
import jdatetime
from dailydriver.display.header.hygiene import get_hygiene_lines


class TestHygiene(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('CREATE TABLE hygiene_config (id INTEGER PRIMARY KEY, item TEXT, desired_interval_days INTEGER, early_warning_enabled INTEGER, show_due_today INTEGER)')
        self.target_date = jdatetime.date.today()

    def tearDown(self):
        self.conn.close()

    def test_not_today_empty(self):
        self.assertEqual(get_hygiene_lines(self.conn, self.target_date, is_today=False), [])

    def test_today_no_items(self):
        self.assertEqual(get_hygiene_lines(self.conn, self.target_date, is_today=True), [])
