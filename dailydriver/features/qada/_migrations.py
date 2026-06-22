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


def _migration_2(conn):
    """Add slot column to qada_entries and backfill for existing prayer entries."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(qada_entries)")
    cols = [row[1] for row in cur.fetchall()]
    if "slot" not in cols:
        cur.execute("ALTER TABLE qada_entries ADD COLUMN slot TEXT")
        # Backfill: derive slot from name for existing prayer entries
        cur.execute("SELECT id, name FROM qada_entries WHERE kind='prayer'")
        for row in cur.fetchall():
            derived = row["name"].lower().replace(" ", "_")
            if derived in ("fajr", "dhuhr_asr", "maghrib_isha"):
                cur.execute("UPDATE qada_entries SET slot=? WHERE id=?", (derived, row["id"]))
    conn.commit()


def _migration_3(conn):
    """Add unique constraint on qada_declines(entry_id, instance_date)."""
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_qada_declines_unique
        ON qada_declines(entry_id, instance_date)
    """)
    conn.commit()


def _migration_4(conn):
    """Add target_total and logged_total columns to qada_entries."""
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(qada_entries)")
    cols = [row[1] for row in cur.fetchall()]
    if "target_total" not in cols:
        cur.execute("ALTER TABLE qada_entries ADD COLUMN target_total INTEGER DEFAULT -1")
    if "logged_total" not in cols:
        cur.execute("ALTER TABLE qada_entries ADD COLUMN logged_total INTEGER DEFAULT 0")
    conn.commit()


def migrations():
    return [_migration_1, _migration_2, _migration_3, _migration_4]
