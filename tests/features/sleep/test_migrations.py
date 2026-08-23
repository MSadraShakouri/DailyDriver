import sqlite3

from dailydriver.features.sleep.migrations import migrations


def test_migration_removes_unique_date_constraint_without_losing_rows():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.execute(
        """CREATE TABLE sleep_logs (
               id INTEGER PRIMARY KEY AUTOINCREMENT,
               jalali_date TEXT UNIQUE NOT NULL,
               sleep_time INTEGER,
               wake_time INTEGER,
               duration_minutes INTEGER
           )"""
    )
    connection.execute(
        "INSERT INTO sleep_logs (jalali_date, duration_minutes) VALUES ('1405-06-01', 60)"
    )
    migrations()[0](connection)
    connection.execute(
        "INSERT INTO sleep_logs (jalali_date, duration_minutes) VALUES ('1405-06-01', 30)"
    )
    assert connection.execute("SELECT COUNT(*) FROM sleep_logs").fetchone()[0] == 2
    connection.close()
