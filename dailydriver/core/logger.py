# dailydriver/core/logger.py
import time
from datetime import datetime
from dailydriver.core.database import get_connection_cm
from dailydriver.core.parser import extract_time
from dailydriver.core.keyword_learner import find_matching_categories
from dailydriver.core.entry_writer import _save_entry, inject_great_categories
from dailydriver.ui.terminal_ui import current_ui

# ----------------------------------------------------------------------
#  Database‑backed state helpers (replaces dot‑file I/O)
# ----------------------------------------------------------------------

def get_last_action_time():
    """Return the Unix timestamp of the last successful write, or None."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key='last_action'")
        row = cur.fetchone()
        return int(row['value']) if row and row['value'] else None

def save_pending_start():
    ts = int(time.time())
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('pending_start', ?)", (str(ts),))
        conn.commit()
    time_str = datetime.fromtimestamp(ts).strftime('%H:%M')
    current_ui.print_line(f"Start saved: {time_str}")

def discard_pending_start():
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key='pending_start'")
        row = cur.fetchone()
        if not row:
            current_ui.print_line("No saved start to discard.")
            return
        ts = int(row['value'])
        time_str = datetime.fromtimestamp(ts).strftime('%H:%M') if ts else "unknown"
        cur.execute("DELETE FROM meta WHERE key='pending_start'")
        conn.commit()
        current_ui.print_line(f"Saved start ({time_str}) discarded.")

def get_pending_start():
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key='pending_start'")
        row = cur.fetchone()
        return int(row['value']) if row and row['value'] else None

def clear_pending_start():
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM meta WHERE key='pending_start'")
        conn.commit()

def start_great_event(categories: list):
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key='great_event_start'")
        if cur.fetchone():
            raise RuntimeError("A great event is already active.")
        ts = int(time.time())
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('great_event_start', ?)", (str(ts),))
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('great_event_categories', ?)", (" ".join(categories),))
        conn.commit()
    return ts

def get_active_great_event():
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key='great_event_start'")
        row_start = cur.fetchone()
        if not row_start:
            return None
        cur.execute("SELECT value FROM meta WHERE key='great_event_categories'")
        row_cats = cur.fetchone()
        start_ts = int(row_start['value'])
        cats = row_cats['value'].split() if row_cats and row_cats['value'].strip() else []
        return start_ts, cats

def clear_great_event():
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM meta WHERE key IN ('great_event_start', 'great_event_categories')")
        conn.commit()

# ----------------------------------------------------------------------
#  Core free‑text logging
# ----------------------------------------------------------------------

def log_free_text(cmd, started_at=None):
    with get_connection_cm() as conn:
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
                    return None
            else:
                started_at = int(time.time())

        # ---------- category suggestion ----------
        matches = find_matching_categories(cmd)
        if matches:
            current_ui.print_line()
            current_ui.print_line("Suggested categories:")
            for i, (path, cnt) in enumerate(matches, 1):
                current_ui.print_line(f"  [{i}] {path}")
            current_ui.print_line("Enter=1, numbers to select, or type new paths (space‑separated)")
            current_ui.print_line()
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

        # ---------- inject great‑event categories ----------
        inject_great_categories(selected_paths)

        # ---------- save entry ----------
        result = _save_entry(conn, cmd, started_at, duration, selected_paths)
        conn.commit()
        return result
