import sqlite3

import jdatetime

from dailydriver.features.birthdays.header import get_birthday_lines


def _connection(*birthdays):
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        "CREATE TABLE birthdays (name TEXT, year INTEGER, month INTEGER, day INTEGER, remind_level INTEGER)"
    )
    connection.executemany("INSERT INTO birthdays VALUES (?,?,?,?,?)", birthdays)
    return connection


def test_today_line_includes_age():
    today = jdatetime.date(1405, 2, 10)
    connection = _connection(("Ali", 1385, 2, 10, 0))
    try:
        assert get_birthday_lines(connection, today) == ["🎂 Ali · 20"]
    finally:
        connection.close()


def test_schedule_filters_and_orders_upcoming_birthdays():
    today = jdatetime.date(1405, 2, 10)
    connection = _connection(
        ("Tomorrow", None, 2, 11, 0),
        ("Week", None, 2, 17, 0),
        ("Hidden", None, 2, 14, 0),
    )
    try:
        assert get_birthday_lines(connection, today) == ["🎈 Tomorrow tomorrow", "🎈 Week in 7 days"]
    finally:
        connection.close()


def test_past_birthday_rolls_into_next_year():
    today = jdatetime.date(1405, 12, 29)
    connection = _connection(("Next year", None, 1, 1, 0))
    try:
        assert get_birthday_lines(connection, today) == ["🎈 Next year tomorrow"]
    finally:
        connection.close()
