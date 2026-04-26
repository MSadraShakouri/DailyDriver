import time
import re
import os
from datetime import datetime
from database import get_connection
from database import commit_and_update
from parser import extract_time

PENDING_FILE = os.path.expanduser('~/.daily_pending')

def load_stopwords():
    """Load stop words from stopwords.txt (located next to this file)."""
    stopwords_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'stopwords.txt')
    stop_set = set()
    try:
        with open(stopwords_path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith('#'):
                    stop_set.add(word.lower())
    except FileNotFoundError:
        # Fallback to a minimal built-in set if file is missing
        stop_set = {'the', 'and', 'for', 'not', 'you', 'but', 'are'}
    return stop_set

# Replace the old STOP_WORDS assignment with a call to load_stopwords()
STOP_WORDS = load_stopwords()

def tokenize(text: str):
    """Return lowercased list of words (simple split)."""
    return text.lower().split()

def find_matching_categories(text: str):
    """Return list of (category_path, match_count) sorted by count desc."""
    conn = get_connection()
    cur = conn.cursor()
    words = tokenize(text)
    # crude partial match: if keyword appears anywhere in any word (or whole text)
    results = {}
    for word in words:
        # search keywords that partially match
        cur.execute(
            "SELECT c.path FROM keywords k JOIN categories c ON k.category_id=c.id WHERE INSTR(?, k.word)>0",
            (word,)
        )
        for row in cur.fetchall():
            path = row['path']
            results[path] = results.get(path, 0) + 1

    conn.close()
    sorted_cats = sorted(results.items(), key=lambda x: x[1], reverse=True)[:3]
    return sorted_cats

def suggest_flags(category_path: str, text: str):
    """Return list of flag tokens that appear in text and are scoped to this category or global."""
    conn = get_connection()
    cur = conn.cursor()
    # get category ID
    cur.execute("SELECT id FROM categories WHERE path=?", (category_path,))
    cat_row = cur.fetchone()
    if not cat_row:
        conn.close()
        return []
    cat_id = cat_row[0]

    # flags where scope is this category or global
    cur.execute("SELECT token, label FROM flags WHERE scope_category_id=? OR scope_category_id IS NULL", (cat_id,))
    flags = cur.fetchall()
    conn.close()

    text_lower = text.lower()
    flagged = []
    for f in flags:
        if f['token'] in text_lower.split():  # exact token match (not partial, to avoid false)
            flagged.append(f['token'])
    return flagged

def learn_keywords(text, category_paths, conn=None):
    if not text or not category_paths:
        return
    words = tokenize(text)
    cleaned = []
    for w in words:
        w = re.sub(r'^[^a-zA-Z]+|[^a-zA-Z]+$', '', w)
        if w in STOP_WORDS:
            continue
        if len(w) < 3: #do not log words under 3 letters
            continue
        if not re.fullmatch(r'[a-zA-Z-]+', w):
            continue
        cleaned.append(w)

    if not cleaned:
        return

    own_conn = False
    if conn is None:
        conn = get_connection()
        own_conn = True
    cur = conn.cursor()

    now_ts = int(time.time())

    for path in category_paths:
        cur.execute("SELECT id FROM categories WHERE path=?", (path,))
        row = cur.fetchone()
        if not row:
            continue
        cat_id = row['id']

        for word in cleaned:
            # 1. Already a permanent keyword? → skip
            cur.execute(
                "SELECT id FROM keywords WHERE word=? AND category_id=?",
                (word, cat_id)
            )
            if cur.fetchone():
                continue

            # 2. Already in pending? → promote to permanent
            cur.execute(
                "SELECT id FROM pending_keywords WHERE word=? AND category_id=?",
                (word, cat_id)
            )
            if cur.fetchone():
                # Promote: delete from pending, insert into keywords
                cur.execute(
                    "DELETE FROM pending_keywords WHERE word=? AND category_id=?",
                    (word, cat_id)
                )
                cur.execute(
                    "INSERT INTO keywords (word, category_id) VALUES (?,?)",
                    (word, cat_id)
                )
                continue

            # 3. First sighting → store as pending
            cur.execute(
                "INSERT OR IGNORE INTO pending_keywords (word, category_id, first_seen) VALUES (?,?,?)",
                (word, cat_id, now_ts)
            )

    if own_conn:
        commit_and_update(conn)
        conn.close()

def get_last_end_time():
    """Return Unix timestamp of the end of the most recent entry, or None."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT started_at, duration_minutes
        FROM entries
        ORDER BY created_at DESC
        LIMIT 1
    ''')
    row = cur.fetchone()
    conn.close()
    if not row or not row['started_at']:
        return None
    end = row['started_at']
    if row['duration_minutes']:
        end += row['duration_minutes'] * 60
    return end

def save_pending_start():
    """Save the current timestamp as a pending start and show the time."""
    import time
    from datetime import datetime
    ts = int(time.time())
    with open(PENDING_FILE, 'w') as f:
        f.write(str(ts))
    time_str = datetime.fromtimestamp(ts).strftime('%H:%M')
    print(f"Start saved: {time_str}")

def discard_pending_start():
    """Clear the pending start and show the time that was discarded."""
    if not os.path.exists(PENDING_FILE):
        print("No saved start to discard.")
        return
    ts = get_pending_start()
    from datetime import datetime
    time_str = datetime.fromtimestamp(ts).strftime('%H:%M') if ts else "unknown"
    clear_pending_start()
    print(f"Saved start ({time_str}) discarded.")

def get_pending_start():
    """Return the saved timestamp, or None if the file doesn't exist."""
    if not os.path.exists(PENDING_FILE):
        return None
    with open(PENDING_FILE, 'r') as f:
        return int(f.read().strip())

def clear_pending_start():
    """Remove the pending start file."""
    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)

def log_free_text(cmd, started_at=None):
    import time
    from datetime import datetime

    conn = get_connection()
    cur = conn.cursor()
    selected_paths = []
    result = ""

    # ---------- step 0 – time handling ----------
    duration = None   # will be set if we have a way to compute it

    if started_at is not None:
        # started_at provided by ln or ee → force duration to now
        duration = int(time.time() - started_at) // 60
        start_dt = datetime.fromtimestamp(started_at)
        start_str = start_dt.strftime('%H:%M')
        dur_str = f"{duration // 60}h {duration % 60}m" if duration // 60 else f"{duration}m"

        print()
        print(f"Time:   {start_str} (from running event)")
        if dur_str:
            print(f"Duration: {dur_str}")
        print("(Enter=yes, n=cancel)")
        confirm = input("> ").strip().lower()
        if confirm != '' and confirm != 'y':
            conn.close()
            return None

    else:
        # Normal entry – try to extract time from the text
        parsed_start, parsed_duration = extract_time(cmd)
        if parsed_start is not None:
            started_at = parsed_start
            if parsed_duration is not None:
                duration = parsed_duration
            start_dt = datetime.fromtimestamp(started_at)
            start_str = start_dt.strftime('%H:%M')
            dur_str = ""
            if duration is not None:
                h = duration // 60
                m = duration % 60
                dur_str = f"{h}h {m}m" if h else f"{m}m"

            print()
            print(f"Time:   {start_str}")
            if dur_str:
                print(f"Duration: {dur_str}")
            print("(Enter=yes, n=cancel)")
            confirm = input("> ").strip().lower()
            if confirm == 'n':
                conn.close()
                return None
        else:
            started_at = int(time.time())

    # ---------- step 1 – category suggestion ----------
    matches = find_matching_categories(cmd)
    if matches:
        print()
        print("Suggested categories:")
        for i, (path, cnt) in enumerate(matches, 1):
            print(f"  [{i}] {path}")
        print("Enter=1, numbers to select, or type new paths (space‑separated)")
        choice = input("> ").strip().lower()
        if choice == '':
            selected_paths = [matches[0][0]]
        else:
            for token in choice.split():
                if token.isdigit():
                    try:
                        idx = int(token) - 1
                        if 0 <= idx < len(matches):
                            selected_paths.append(matches[idx][0])
                    except ValueError:
                        pass
                else:
                    cur.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (token,))
                    commit_and_update(conn)
                    selected_paths.append(token)
    else:
        cat_choice = input("No suggestions. Enter category path (or Enter to skip): ").strip().lower()
        if cat_choice:
            for token in cat_choice.split():
                if token:
                    cur.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (token,))
                    commit_and_update(conn)
                    selected_paths.append(token)

    # ---------- step 2 – insert entry ----------
    cur.execute(
        "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
        (int(time.time()), started_at, duration, cmd)
    )
    entry_id = cur.lastrowid

    for path in selected_paths:
        cur.execute("SELECT id FROM categories WHERE path=?", (path,))
        row = cur.fetchone()
        if row:
            cur.execute("INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)",
                        (entry_id, row['id']))

    # ---------- step 3 – flags ----------
    print("\nFlags? (Enter=none, or type tokens)")
    flag_input = input("> ").strip().lower()
    attached_flags = []
    if flag_input:
        tokens = flag_input.split()
        for token in tokens:
            cur.execute("SELECT id FROM flags WHERE token=?", (token,))
            frow = cur.fetchone()
            if frow:
                cur.execute("INSERT INTO entry_flags (entry_id, flag_id) VALUES (?,?)",
                            (entry_id, frow['id']))
                attached_flags.append(token)
            else:
                from flags_manager import create_flag_interactive
                print("\n(Press Ctrl+C to cancel flag creation)")
                default_scope = selected_paths[0] if selected_paths else None
                try:
                    flag_id = create_flag_interactive(token, default_scope_path=default_scope, conn=conn)
                except KeyboardInterrupt:
                    print("Cancelled.")
                    continue
                if flag_id is not None:
                    cur.execute("INSERT INTO entry_flags (entry_id, flag_id) VALUES (?,?)",
                                (entry_id, flag_id))
                    attached_flags.append(token)

    # ---------- step 4 – learn keywords ----------
    learn_keywords(cmd, selected_paths, conn=conn)
    commit_and_update(conn)
    conn.close()

    # ---------- build result string ----------
    if selected_paths:
        result += "Logged:\n"
        for p in selected_paths:
            result += f"  {p}\n"
    if started_at:
        start_dt = datetime.fromtimestamp(started_at)
        result += f"Time:   {start_dt.strftime('%H:%M')}\n"
    if duration is not None and duration > 0:
        h = duration // 60
        m = duration % 60
        result += f"Duration: {h}h {m}m\n" if h else f"Duration: {m}m\n"
    if attached_flags:
        result += f"Flags:  {', '.join(attached_flags)}\n"
    return result.strip()
