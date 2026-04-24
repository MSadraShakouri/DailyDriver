import sqlite3

DB_NAME = "daily.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_connection()
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
            description TEXT,
            is_multiline BOOLEAN DEFAULT 0
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
            desired_interval_days INTEGER
        )
    ''')
    conn.commit()
    conn.close()
