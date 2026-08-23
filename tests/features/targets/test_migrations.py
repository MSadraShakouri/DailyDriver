import sqlite3

from dailydriver.features.targets.migrations import migrations


def test_migrations_build_current_schema():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        for migration in migrations():
            migration(connection)
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(target_entries)")
        }
        assert "last_counter_value" in columns
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='target_logs'"
        ).fetchone()
    finally:
        connection.close()


def test_counter_migration_is_idempotent_after_first_application():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        first, second = migrations()
        first(connection)
        second(connection)
        second(connection)
        names = [row["name"] for row in connection.execute("PRAGMA table_info(target_entries)")]
        assert names.count("last_counter_value") == 1
    finally:
        connection.close()
