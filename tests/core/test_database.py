"""Database connection and isolation contracts."""

import sqlite3

from dailydriver.core.database import get_connection, get_connection_cm, get_db_path


def test_environment_selects_test_database(db_path):
    assert get_db_path() == str(db_path)


def test_migrated_database_contains_required_tables(db_path):
    with get_connection_cm(auto=False) as connection:
        tables = {
            row["name"]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert {
        "categories",
        "entries",
        "hygiene_config",
        "prayer_logs",
        "sleep_logs",
        "qada_entries",
        "target_entries",
    } <= tables


def test_connection_enables_foreign_keys(db_path):
    connection = get_connection(auto=False)
    try:
        assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1
        assert connection.row_factory is sqlite3.Row
    finally:
        connection.close()


def test_context_manager_closes_connection(db_path):
    with get_connection_cm(auto=False) as connection:
        connection.execute("SELECT 1")
    try:
        connection.execute("SELECT 1")
    except sqlite3.ProgrammingError as error:
        assert "closed" in str(error).lower()
    else:
        raise AssertionError("database context manager left its connection open")
