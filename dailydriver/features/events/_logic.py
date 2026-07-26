# dailydriver/features/events/_logic.py
import time
from datetime import datetime

from dailydriver.core.database import get_connection_cm
from dailydriver.core.logger import log_free_text  # still in core for now
from dailydriver.ui.terminal_ui import current_ui


# ---------- state helpers (moved from core/logger.py) ----------
def get_last_action_time():
    """Return the Unix timestamp of the last successful write, or None."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key='last_action'")
        row = cur.fetchone()
        return int(row["value"]) if row and row["value"] else None


def save_pending_start():
    ts = int(time.time())
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('pending_start', ?)",
            (str(ts),),
        )
        conn.commit()
    time_str = datetime.fromtimestamp(ts).strftime("%H:%M")
    return f"Start saved: {time_str}"


def discard_pending_start():
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key='pending_start'")
        row = cur.fetchone()
        if not row:
            return "No saved start to discard."
        ts = int(row["value"])
        time_str = datetime.fromtimestamp(ts).strftime("%H:%M") if ts else "unknown"
        cur.execute("DELETE FROM meta WHERE key='pending_start'")
        conn.commit()
        return f"Saved start ({time_str}) discarded."


def get_pending_start():
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key='pending_start'")
        row = cur.fetchone()
        return int(row["value"]) if row and row["value"] else None


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
        cur.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('great_event_start', ?)",
            (str(ts),),
        )
        cur.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('great_event_categories', ?)",
            (" ".join(categories),),
        )
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
        start_ts = int(row_start["value"])
        cats = row_cats["value"].split() if row_cats and row_cats["value"].strip() else []
        return start_ts, cats


def clear_great_event():
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM meta WHERE key IN ('great_event_start', 'great_event_categories')")
        conn.commit()


# ---------- end of state helpers ----------


# ---------- command wrappers (from cli/commands/events.py) ----------
def log_event_end(cmd):
    started_at = get_pending_start()
    if started_at is None:
        return "No running event to end."

    parts = cmd.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""

    result = log_free_text(text, started_at=started_at)
    if result is not None:
        clear_pending_start()
        return result
    return None


def log_chain_now(line):
    last_ts = get_last_action_time()
    if last_ts is None:
        return "No previous action to chain from."

    parts = line.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""
    return log_free_text(text, started_at=last_ts)


def start_great_event_cmd(line):
    if get_active_great_event() is not None:
        current_ui.print_line("A great event is already active. Cancel it first (cge).")
        return None

    parts = line.strip().split(maxsplit=1)
    if len(parts) > 1:
        cat_str = parts[1].strip()
        cats = cat_str.split() if cat_str else []
    else:
        cat_input = current_ui.prompt("Great event categories (space‑separated): ").strip()
        cats = cat_input.split() if cat_input else []

    if not cats:
        current_ui.print_line("No categories entered. Great event not started.")
        return None

    cats = [c.lower() for c in cats]
    try:
        ts = start_great_event(cats)
    except RuntimeError as e:
        current_ui.print_line(str(e))
        return None

    time_str = datetime.fromtimestamp(ts).strftime("%H:%M")
    return f"Great event started at {time_str} with: {', '.join(cats)}"


def end_great_event_cmd(line):
    ge = get_active_great_event()
    if ge is None:
        current_ui.print_line("No great event is active.")
        return None
    start_ts, _ = ge

    parts = line.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""

    result = log_free_text(text, started_at=start_ts)

    if result is not None:
        clear_great_event()
    return result


def cancel_great_event_cmd(_=None):
    ge = get_active_great_event()
    if ge is None:
        current_ui.print_line("No great event active.")
        return None
    clear_great_event()
    return "Great event cancelled."


def update_last_action() -> str:
    """Update last_action meta timestamp to now. Returns confirmation string."""
    import time
    from datetime import datetime

    ts = int(time.time())
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_action', ?)", (str(ts),))
        conn.commit()
    return f"Last action updated to {datetime.fromtimestamp(ts).strftime('%H:%M')}"
