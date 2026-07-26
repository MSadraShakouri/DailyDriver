"""Targets feature migrations."""


def _migration_1(conn):
    conn.execute("""
        CREATE TABLE target_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL CHECK(kind IN ('nazr', 'habit')),
            name TEXT UNIQUE NOT NULL,
            target_total INTEGER,
            logged_total INTEGER NOT NULL DEFAULT 0,
            interval_type TEXT,
            interval_value INTEGER,
            target_per_interval INTEGER,
            paused_until TEXT,
            created_at INTEGER NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE target_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entry_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            instance_date TEXT NOT NULL,
            logged_at INTEGER NOT NULL,
            FOREIGN KEY (entry_id) REFERENCES target_entries(id) ON DELETE CASCADE
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_target_logs_entry_date ON target_logs(entry_id, instance_date)
    """)
    conn.commit()


def _migration_2(conn):
    """Add last_counter_value column to target_entries."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(target_entries)")
    columns = [row[1] for row in cur.fetchall()]
    if "last_counter_value" not in columns:
        cur.execute("ALTER TABLE target_entries ADD COLUMN last_counter_value INTEGER DEFAULT 0")
    conn.commit()


def migrations():
    return [_migration_1, _migration_2]
