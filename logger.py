import time
import re
import os
from datetime import datetime
from database import get_connection
from parser import extract_time
from ui import current_ui

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
PENDING_FILE = os.path.join(BASE_DIR, '.daily_pending')
LAST_ACTION_FILE = os.path.join(BASE_DIR, '.daily_last_action')
GREAT_EVENT_FILE = os.path.join(BASE_DIR, '.daily_great_event')

# ----------------------------------------------------------------------
#  Last‑action file helpers
# ----------------------------------------------------------------------
def get_last_action_time():
    """Return the Unix timestamp of the last successful write, or None."""
    try:
        with open(LAST_ACTION_FILE, 'r') as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None

# ----------------------------------------------------------------------
#  Stop‑word loading
# ----------------------------------------------------------------------
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
        stop_set = {'the', 'and', 'for', 'not', 'you', 'but', 'are'}
    return stop_set

STOP_WORDS = load_stopwords()

# ----------------------------------------------------------------------
#  Tokenisation & matching
# ----------------------------------------------------------------------
def tokenize(text: str):
    """Return lowercased list of words (simple split)."""
    return text.lower().split()

def find_matching_categories(text: str):
    """Return list of (category_path, match_count) sorted by count desc."""
    conn = get_connection()
    cur = conn.cursor()
    words = tokenize(text)
    results = {}
    for word in words:
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
    cur.execute("SELECT id FROM categories WHERE path=?", (category_path,))
    cat_row = cur.fetchone()
    if not cat_row:
        conn.close()
        return []
    cat_id = cat_row[0]
    cur.execute("SELECT token, label FROM flags WHERE scope_category_id=? OR scope_category_id IS NULL", (cat_id,))
    flags = cur.fetchall()
    conn.close()
    text_lower = text.lower()
    flagged = []
    for f in flags:
        if f['token'] in text_lower.split():
            flagged.append(f['token'])
    return flagged

# ----------------------------------------------------------------------
#  Keyword learning
# ----------------------------------------------------------------------
def learn_keywords(text, category_paths, conn=None):
    if not text or not category_paths:
        return
    words = tokenize(text)
    cleaned = []
    for w in words:
        w = re.sub(r'^[^a-zA-Z]+|[^a-zA-Z]+$', '', w)
        if w in STOP_WORDS:
            continue
        if len(w) < 3:
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
            cur.execute("SELECT id FROM keywords WHERE word=? AND category_id=?", (word, cat_id))
            if cur.fetchone():
                continue
            cur.execute("SELECT id FROM pending_keywords WHERE word=? AND category_id=?", (word, cat_id))
            if cur.fetchone():
                cur.execute("DELETE FROM pending_keywords WHERE word=? AND category_id=?", (word, cat_id))
                cur.execute("INSERT INTO keywords (word, category_id) VALUES (?,?)", (word, cat_id))
                continue
            cur.execute("INSERT OR IGNORE INTO pending_keywords (word, category_id, first_seen) VALUES (?,?,?)",
                        (word, cat_id, now_ts))
    if own_conn:
        conn.commit()
        conn.close()

# ----------------------------------------------------------------------
#  Pending start helpers (se / ee / ce)
# ----------------------------------------------------------------------
def save_pending_start():
    ts = int(time.time())
    with open(PENDING_FILE, 'w') as f:
        f.write(str(ts))
    time_str = datetime.fromtimestamp(ts).strftime('%H:%M')
    current_ui.print_line(f"Start saved: {time_str}")

def discard_pending_start():
    if not os.path.exists(PENDING_FILE):
        current_ui.print_line("No saved start to discard.")
        return
    ts = get_pending_start()
    time_str = datetime.fromtimestamp(ts).strftime('%H:%M') if ts else "unknown"
    clear_pending_start()
    current_ui.print_line(f"Saved start ({time_str}) discarded.")

def get_pending_start():
    if not os.path.exists(PENDING_FILE):
        return None
    with open(PENDING_FILE, 'r') as f:
        return int(f.read().strip())

def clear_pending_start():
    if os.path.exists(PENDING_FILE):
        os.remove(PENDING_FILE)

# ----------------------------------------------------------------------
#  Great‑event helpers (sge / ege / cge)
# ----------------------------------------------------------------------
def start_great_event(categories: list):
    """Save a great event start timestamp and its categories.
    Raises RuntimeError if one is already active."""
    if os.path.exists(GREAT_EVENT_FILE):
        raise RuntimeError("A great event is already active.")
    ts = int(time.time())
    with open(GREAT_EVENT_FILE, 'w') as f:
        f.write(f"{ts}\n")
        f.write(" ".join(categories))
    return ts

def get_active_great_event():
    """Return (start_ts, [category_path, ...]) or None."""
    if not os.path.exists(GREAT_EVENT_FILE):
        return None
    with open(GREAT_EVENT_FILE, 'r') as f:
        lines = f.read().splitlines()
    if len(lines) < 2:
        return None
    start_ts = int(lines[0])
    cats = lines[1].split() if lines[1].strip() else []
    return start_ts, cats

def clear_great_event():
    """Delete the great event state file."""
    if os.path.exists(GREAT_EVENT_FILE):
        os.remove(GREAT_EVENT_FILE)

def inject_great_categories(selected_paths: list):
    """If a great event is active, append its categories to selected_paths (no duplicates)."""
    active = get_active_great_event()
    if active:
        _, ge_cats = active
        for cat in ge_cats:
            if cat not in selected_paths:
                selected_paths.append(cat)

# ----------------------------------------------------------------------
#  Internal save
# ----------------------------------------------------------------------
def _save_entry(conn, cmd, started_at, duration, selected_paths, attached_flags):
    cur = conn.cursor()
    now_ts = int(time.time())

    cur.execute(
        "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
        (now_ts, started_at, duration, cmd)
    )
    entry_id = cur.lastrowid

    for path in selected_paths:
        cur.execute("SELECT id FROM categories WHERE path=?", (path,))
        row = cur.fetchone()
        if row:
            cur.execute("INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)",
                        (entry_id, row['id']))

    for token in attached_flags:
        cur.execute("SELECT id FROM flags WHERE token=?", (token,))
        frow = cur.fetchone()
        if frow:
            cur.execute("INSERT INTO entry_flags (entry_id, flag_id) VALUES (?,?)",
                        (entry_id, frow['id']))

    learn_keywords(cmd, selected_paths, conn=conn)

    result = ""
    if selected_paths:
        result += "Logged:\n"
        for p in selected_paths:
            result += f"  {p}\n"
    if started_at is not None:
        start_dt = datetime.fromtimestamp(started_at)
        result += f"Time:   {start_dt.strftime('%H:%M')}\n"
    if duration is not None and duration > 0:
        h = duration // 60
        m = duration % 60
        result += f"Duration: {h}h {m}m\n" if h else f"Duration: {m}m\n"
    if attached_flags:
        result += f"Flags:  {', '.join(attached_flags)}\n"
    return result.strip()

# ----------------------------------------------------------------------
#  Core free‑text logging
# ----------------------------------------------------------------------
def log_free_text(cmd, started_at=None):
    conn = get_connection()
    cur = conn.cursor()
    selected_paths = []
    duration = None

    # ---------- step 0 – time handling ----------
    if started_at is not None:
        duration = int(time.time() - started_at) // 60
        start_dt = datetime.fromtimestamp(started_at)
        start_str = start_dt.strftime('%H:%M')
        dur_str = f"{duration // 60}h {duration % 60}m" if duration // 60 else f"{duration}m"
        if not current_ui.confirm_time(start_str, dur_str):
            conn.close()
            return None
    else:
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
            if not current_ui.confirm_time(start_str, dur_str):
                conn.close()
                return None
        else:
            started_at = int(time.time())

    # ---------- step 1 – category suggestion ----------
    matches = find_matching_categories(cmd)
    if matches:
        current_ui.print_line()
        current_ui.print_line("Suggested categories:")
        for i, (path, cnt) in enumerate(matches, 1):
            current_ui.print_line(f"  [{i}] {path}")
        current_ui.print_line("Enter=1, numbers to select, or type new paths (space‑separated)")
        choice = current_ui.prompt("> ").strip().lower()
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
                    conn.commit()
                    selected_paths.append(token)
    else:
        cat_choice = current_ui.prompt("No suggestions. Enter category path (or Enter to skip): ").strip().lower()
        if cat_choice:
            for token in cat_choice.split():
                if token:
                    cur.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (token,))
                    conn.commit()
                    selected_paths.append(token)

    # ---------- step 2 – flags ----------
    attached_flags = []
    current_ui.print_line("\nFlags? (Enter=none, or type tokens)")
    flag_input = current_ui.prompt("> ").strip().lower()
    if flag_input:
        tokens = flag_input.split()
        for token in tokens:
            attached_flags.append(token)

    # ---------- inject great‑event categories ----------
    inject_great_categories(selected_paths)

    # ---------- step 3 – save entry ----------
    result = _save_entry(conn, cmd, started_at, duration, selected_paths, attached_flags)
    conn.commit()
    conn.close()
    return result
