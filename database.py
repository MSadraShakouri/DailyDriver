import sqlite3
import time
import os
from ui import current_ui

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
DB_NAME = os.path.join(BASE_DIR, "daily.db")

# file that stores the timestamp of the last successful write
LAST_ACTION_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)), '.daily_last_action')

def get_last_hygiene_time(conn, item):
    """
    Return the Unix timestamp of the most recent hygiene log for `item`,
    or None if no log exists.  The hygiene category is expected to be named
    exactly `.../item` (e.g., `hygiene/shower`).
    """
    cur = conn.cursor()
    cur.execute('''
        SELECT MAX(e.started_at) as last_time
        FROM entries e
        JOIN entry_categories ec ON e.id = ec.entry_id
        JOIN categories c ON ec.category_id = c.id
        WHERE c.path LIKE ?
    ''', ('%/' + item,))
    row = cur.fetchone()
    return row['last_time'] if (row and row['last_time']) else None

class _AutoCommitConnection:
    """Wraps a sqlite3 connection, updating the last‑action file on commit()."""
    def __init__(self, conn):
        self._conn = conn

    def commit(self):
        self._conn.commit()
        try:
            with open(LAST_ACTION_FILE, 'w') as f:
                f.write(str(int(time.time())))
        except Exception:
            pass

    def close(self):
        self._conn.close()

    # Delegate everything else to the real connection
    def __getattr__(self, name):
        return getattr(self._conn, name)

def get_connection(auto=True):
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    if not auto:
        return conn
    # otherwise wrap it to auto‑update the last‑action file on commit
    return _AutoCommitConnection(conn)

def init_db():
    conn = get_connection(auto=False)
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

    # ---------- flags ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS flags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT NOT NULL,
            label TEXT,
            scope_category_id INTEGER,
            FOREIGN KEY (scope_category_id) REFERENCES categories(id)
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

    # ---------- entry_categories (many-to-many) ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS entry_categories (
            entry_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,
            PRIMARY KEY (entry_id, category_id),
            FOREIGN KEY (entry_id) REFERENCES entries(id),
            FOREIGN KEY (category_id) REFERENCES categories(id)
        )
    ''')

    # ---------- entry_flags (many-to-many) ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS entry_flags (
            entry_id INTEGER NOT NULL,
            flag_id INTEGER NOT NULL,
            PRIMARY KEY (entry_id, flag_id),
            FOREIGN KEY (entry_id) REFERENCES entries(id),
            FOREIGN KEY (flag_id) REFERENCES flags(id)
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
            prayer_time INTEGER,   -- Unix timestamp of the actual prayer (nullable)
            UNIQUE(prayer_slot, jalali_date)
        )
    ''')

    # --- migration: add jamaat / shak columns to prayer_logs ---
    try:
        cur.execute("ALTER TABLE prayer_logs ADD COLUMN jamaat_location TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE prayer_logs ADD COLUMN shak_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

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

    # ---------- hygiene config (desired interval) ----------
    cur.execute('''
        CREATE TABLE IF NOT EXISTS hygiene_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item TEXT UNIQUE NOT NULL,
            desired_interval_days INTEGER,
            early_warning_enabled INTEGER DEFAULT 1,
            show_due_today INTEGER DEFAULT 1
        )
    ''')

    # ---------- migration: add columns if missing ----------
    try:
        cur.execute("ALTER TABLE hygiene_config ADD COLUMN early_warning_enabled INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass
    try:
        cur.execute("ALTER TABLE hygiene_config ADD COLUMN show_due_today INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    cur.execute("UPDATE hygiene_config SET early_warning_enabled = 1 WHERE early_warning_enabled IS NULL")
    cur.execute("UPDATE hygiene_config SET show_due_today = 0 WHERE show_due_today IS NULL")

    # ---------- pending_keywords (two‑sighting promotion) ----------
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

    # Performance indexes for long-term use
    cur.execute('CREATE INDEX IF NOT EXISTS idx_entries_created_at ON entries(created_at)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_entries_started_at ON entries(started_at)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_entry_categories_category ON entry_categories(category_id)')

    conn.commit()
    conn.close()


def cleanup_pending_keywords():
    """Delete pending keywords older than 14 days."""
    conn = get_connection(auto=False)
    cur = conn.cursor()
    cur.execute("DELETE FROM pending_keywords WHERE first_seen < unixepoch() - 1209600")
    conn.commit()
    conn.close()
