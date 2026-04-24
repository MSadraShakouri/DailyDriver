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
    seed_data()
    conn.commit()
    conn.close()

def seed_data():
    conn = get_connection()
    cur = conn.cursor()

    # Check if already seeded
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] > 0:
        conn.close()
        return

    # --- categories ---
    categories = [
        'hygiene/shower',
        'hygiene/shaving',
        'hygiene/brushing_teeth',
        'hygiene/face_wash',
        'cec',                     # explicit content consumption
        'entertainment/cube',
        'entertainment/game',
        'family',
        'programming',
        'thought',
    ]
    for cat_path in categories:
        cur.execute("INSERT INTO categories (path) VALUES (?)", (cat_path,))

    # --- keywords (word → category) ---
    kw_map = [
        ('showered', 'hygiene/shower'),
        ('shower',   'hygiene/shower'),
        ('bath',     'hygiene/shower'),
        ('shaved',   'hygiene/shaving'),
        ('shave',    'hygiene/shaving'),
        ('beard',    'hygiene/shaving'),
        ('pub',      'hygiene/shaving'),   # you know
        ('brushed',  'hygiene/brushing_teeth'),
        ('teeth',    'hygiene/brushing_teeth'),
        ('face',     'hygiene/face_wash'),
        ('washed',   'hygiene/face_wash'),
        ('cec',      'cec'),
        ('hent',     'cec'),
        ('hentai',   'cec'),
        ('cube',     'entertainment/cube'),
        ('rubik',    'entertainment/cube'),
        ('tekken',   'entertainment/game'),
        ('game',     'entertainment/game'),
        ('baba',     'family'),
        ('grandpa',  'family'),
        ('mom',      'family'),
        ('code',     'programming'),
        ('program',  'programming'),
        ('python',   'programming'),
        ('thought',  'thought'),
        ('thinking', 'thought'),
    ]
    for word, cat_path in kw_map:
        # get category ID
        cur.execute("SELECT id FROM categories WHERE path=?", (cat_path,))
        cat_id = cur.fetchone()[0]
        cur.execute("INSERT INTO keywords (word, category_id) VALUES (?,?)", (word, cat_id))

    # --- flags ---
    flags = [
        ('m', 'masturbation', 'hygiene/shower'),
        ('m', 'masturbation', 'cec'),
        ('s', 'sweat',        'hygiene/shower'),
        ('late', 'late',      None),   # global
    ]
    for token, label, scope_path in flags:
        scope_id = None
        if scope_path:
            cur.execute("SELECT id FROM categories WHERE path=?", (scope_path,))
            row = cur.fetchone()
            if row:
                scope_id = row[0]
        cur.execute("INSERT INTO flags (token, label, scope_category_id) VALUES (?,?,?)",
                    (token, label, scope_id))

    conn.commit()
    conn.close()
