"""Persistent state for chaining and long-running events."""
import time
from datetime import datetime

from dailydriver.core.database import get_connection_cm


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





def update_last_action() -> str:
    """Update last_action meta timestamp to now. Returns confirmation string."""
    ts = int(time.time())
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_action', ?)", (str(ts),))
        conn.commit()
    return f"Last action updated to {datetime.fromtimestamp(ts).strftime('%H:%M')}"
