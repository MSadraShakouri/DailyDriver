# dailydriver/features/qada/_migrations.py
"""Qada feature migrations."""


def _migration_1(conn):
    """Create qada_entries, qada_logs, and qada_declines tables."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qada_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('prayer', 'fasting')),
            interval_type TEXT,
            interval_value TEXT,
            interval_calendar TEXT DEFAULT 'jalali',
            paused_from TEXT,
            paused_until TEXT,
            created_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qada_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            amount INTEGER NOT NULL DEFAULT 1,
            instance_date TEXT NOT NULL,
            logged_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            FOREIGN KEY (entry_id) REFERENCES qada_entries(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS qada_declines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            instance_date TEXT NOT NULL,
            logged_at INTEGER NOT NULL DEFAULT (strftime('%s', 'now')),
            FOREIGN KEY (entry_id) REFERENCES qada_entries(id) ON DELETE CASCADE
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_qada_logs_entry_date ON qada_logs(entry_id, instance_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_qada_declines_entry_date ON qada_declines(entry_id, instance_date)")
    conn.commit()


def migrations():
    return [_migration_1]
