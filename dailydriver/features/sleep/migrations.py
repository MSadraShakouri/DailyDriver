"""Sleep feature migrations."""


def _migration_1(conn):
    """Remove UNIQUE constraint from jalali_date in sleep_logs."""
    # Check if the UNIQUE constraint exists by checking the schema
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(sleep_logs)")
    cols = cur.fetchall()
    # Find the jalali_date column and check if it has 'UNIQUE'
    # SQLite doesn't expose UNIQUE directly in PRAGMA table_info,
    # but we can check if there's a unique index or constraint.
    # Simpler: create new table without the constraint.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sleep_logs_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jalali_date TEXT NOT NULL,
            sleep_time INTEGER,
            wake_time INTEGER,
            duration_minutes INTEGER
        )
    """)
    cur.execute("""
        INSERT INTO sleep_logs_new (id, jalali_date, sleep_time, wake_time, duration_minutes)
        SELECT id, jalali_date, sleep_time, wake_time, duration_minutes FROM sleep_logs
    """)
    cur.execute("DROP TABLE sleep_logs")
    cur.execute("ALTER TABLE sleep_logs_new RENAME TO sleep_logs")
    conn.commit()


def migrations():
    return [_migration_1]
