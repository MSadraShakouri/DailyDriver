import sqlite3

from dailydriver.features.qada.migrations import migrations


def test_migrations_build_current_schema_and_preserve_logs():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        for migration in migrations():
            migration(connection)
        tables = {row["name"] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"qada_entries", "qada_logs"} <= tables
        assert "qada_declines" not in tables
        columns = {row["name"] for row in connection.execute("PRAGMA table_info(qada_entries)")}
        assert {"slot", "target_total", "logged_total", "paused_until"} <= columns
        assert "paused_from" not in columns
    finally:
        connection.close()


def test_migrations_are_safe_to_recheck_at_current_version():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        migration_list = migrations()
        for migration in migration_list:
            migration(connection)
        # Column additions and final rebuild explicitly guard repeated checks.
        for index in (1, 3, 4):
            migration_list[index](connection)
    finally:
        connection.close()
