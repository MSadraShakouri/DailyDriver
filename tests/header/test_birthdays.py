# tests/header/test_birthdays.py
import sqlite3
import unittest

import jdatetime

from dailydriver.features.birthdays._header import get_birthday_lines


class TestBirthdays(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.execute(
            "CREATE TABLE birthdays (id INTEGER PRIMARY KEY, name TEXT, month INTEGER, day INTEGER, year INTEGER, remind_level INTEGER DEFAULT 0)"
        )
        self.target_date = jdatetime.date(1405, 2, 21)

    def tearDown(self):
        self.conn.close()

    def test_birthday_today(self):
        self.conn.execute(
            "INSERT INTO birthdays (name, month, day, year, remind_level) VALUES ('Ali', 2, 21, 1386, 1)"
        )
        lines = get_birthday_lines(self.conn, self.target_date)
        self.assertTrue(any("Ali" in line for line in lines))
        self.assertTrue(any("🎂" in line for line in lines))

    def test_birthday_in_future(self):
        self.conn.execute(
            "INSERT INTO birthdays (name, month, day, year, remind_level) VALUES ('Zahra', 2, 24, 1380, 1)"
        )
        lines = get_birthday_lines(self.conn, self.target_date)
        self.assertTrue(any("Zahra" in line for line in lines))
