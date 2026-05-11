import unittest
import sqlite3
import jdatetime
from dailydriver.display.header.birthdays import get_birthday_str


class TestBirthdays(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.conn.execute('CREATE TABLE birthdays (id INTEGER PRIMARY KEY, name TEXT, month INTEGER, day INTEGER, year INTEGER)')
        self.target_date = jdatetime.date(1405, 2, 21)

    def tearDown(self):
        self.conn.close()

    def test_birthday_today(self):
        self.conn.execute("INSERT INTO birthdays (name, month, day, year) VALUES ('Ali', 2, 21, 1386)")
        s = get_birthday_str(self.conn, self.target_date)
        self.assertIn('Ali', s)
        self.assertIn('🎂', s)

    def test_birthday_in_future(self):
        self.conn.execute("INSERT INTO birthdays (name, month, day, year) VALUES ('Zahra', 2, 25, 1380)")
        s = get_birthday_str(self.conn, self.target_date)
        self.assertIn('Zahra', s)
        self.assertIn('🎈4d', s)
