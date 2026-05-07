# dailydriver/core/migration.py
"""Lightweight schema migration system."""
from dailydriver.core.database import get_connection


def _migration_1(conn):
    """Create all tables and columns as of version 1."""
    cur = conn.cursor()

    # ---------- categories ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL
        )
    ''')

    # ---------- keywords ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # ---------- entries ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at INTEGER NOT NULL,
            started_at INTEGER,
            duration_minutes INTEGER,
            description TEXT
        )
    ''')

    # ---------- entry_categories ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS entry_categories (
            entry_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            PRIMARY KEY (entry_id, category_id),
            FOREIGN KEY (entry_id) REFERENCES entries(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # ---------- prayer_logs ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS prayer_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prayer_slot TEXT NOT NULL,
            jalali_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('on_time','qada','missed')),
            logged_at INTEGER,
            prayer_time INTEGER,
            jamaat_location TEXT,
            shak_count INTEGER DEFAULT 0,
            UNIQUE(prayer_slot, jalali_date)
        )
    ''')

    # ---------- sleep_logs ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sleep_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jalali_date TEXT UNIQUE NOT NULL,
            sleep_time INTEGER,
            wake_time INTEGER,
            duration_minutes INTEGER
        )
    ''')

    # ---------- birthdays ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS birthdays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            day INTEGER NOT NULL,
            month INTEGER NOT NULL,
            year INTEGER
        )
    ''')

    # ---------- intentions ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS intentions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            deadline INTEGER,
            expected_duration_minutes INTEGER
        )
    ''')

    # ---------- hygiene_config ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS hygiene_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT UNIQUE NOT NULL,
            desired_interval_days INTEGER,
            early_warning_enabled INTEGER DEFAULT 1,
            show_due_today INTEGER DEFAULT 1
        )
    ''')

    # ---------- pending_keywords ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pending_keywords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            word TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            first_seen INTEGER NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(id),
            UNIQUE(word, category_id)
        )
    ''')

    # --- old flag tables removed ---
    cur.execute("DROP TABLE IF EXISTS entry_flags")
    cur.execute("DROP TABLE IF EXISTS flags")

    # Performance indexes
    cur.execute('CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_entries_started_at ON entries(started_at)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_entry_categories_category ON entry_categories(category_id)')

    conn.commit()

def _migration_2(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS nap_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jalali_date TEXT NOT NULL,
            start_time INTEGER NOT NULL,
            duration_minutes INTEGER,
            description TEXT
        )
    ''')
    conn.commit()

def _migration_3(conn):
    cur = conn.cursor()
    # add count column to keywords
    cur.execute("ALTER TABLE keywords ADD COLUMN count INTEGER DEFAULT 1")
    cur.execute("UPDATE keywords SET count = 1 WHERE count IS NULL")
    # delete the old pending_keywords table
    cur.execute("DROP TABLE IF EXISTS pending_keywords")
    conn.commit()

def _migration_4(conn):
    """Create FTS5 index on entries.description."""
    cur = conn.cursor()
    cur.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS entries_fts USING fts5(
            description,
            content='entries',
            content_rowid='id'
        );
    """)
    conn.commit()

def _migration_5(conn):
    """Stem all existing keywords and merge duplicates."""
    from porter2stemmer import Porter2Stemmer
    stemmer = Porter2Stemmer()
    cur = conn.cursor()

    # Step 1 – stem every word in the keywords table
    rows = cur.execute("SELECT id, word FROM keywords").fetchall()
    for r in rows:
        cur.execute(
            "UPDATE keywords SET word = ? WHERE id = ?",
            (stemmer.stem(r["word"]), r["id"])
        )

    # Step 2 – merge duplicates: same (word, category_id) -> keep smallest id, sum counts
    cur.execute("""
        SELECT word, category_id, MIN(id) AS keep_id, SUM(count) AS total_count
        FROM keywords
        GROUP BY word, category_id
        HAVING COUNT(*) > 1
    """)
    for row in cur.fetchall():
        cur.execute(
            "UPDATE keywords SET count = ? WHERE id = ?",
            (row["total_count"], row["keep_id"])
        )
        cur.execute(
            "DELETE FROM keywords WHERE word = ? AND category_id = ? AND id != ?",
            (row["word"], row["category_id"], row["keep_id"])
        )

    conn.commit()

def _migration_6(conn):
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS weather_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL DEFAULT 'Tehran',
            temp_c INTEGER NOT NULL,
            condition_fa TEXT NOT NULL,
            timestamp INTEGER NOT NULL
        )
    ''')
    conn.commit()

def _migration_7(conn):
    """Rebuild the FTS5 index to include any entries that were missed during v4."""
    conn.execute("INSERT INTO entries_fts(entries_fts) VALUES('rebuild')")
    conn.commit()

_MIGRATIONS = {
    1: _migration_1,
    2: _migration_2,
    3: _migration_3,
    4: _migration_4,
    5: _migration_5,
    6: _migration_6,
    7: _migration_7,
}

def _get_current_version(conn):
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER)")
    cur.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
    row = cur.fetchone()
    return row['version'] if row else 0


def _set_version(conn, version):
    cur = conn.cursor()
    cur.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
    conn.commit()


def run_migrations():
    """Apply all pending schema migrations."""
    conn = get_connection(auto=False)   # use the un‑wrapped connection directly
    try:
        current = _get_current_version(conn)
        for version in sorted(_MIGRATIONS.keys()):
            if version > current:
                _MIGRATIONS[version](conn)
                _set_version(conn, version)
    finally:
        conn.close()
