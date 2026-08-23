"""Persistence and lifecycle operations for target entries."""

import time

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.features.presentation import is_paused

from . import clock


def add_entry(
    kind: str,
    name: str,
    target_total: int | None = None,
    interval_type: str | None = None,
    interval_value: int | None = None,
    target_per_interval: int | None = None,
) -> int:
    """Add a new target entry. Returns the new entry ID."""
    if kind not in ("nazr", "habit"):
        raise ValueError("kind must be 'nazr' or 'habit'")

    if target_total is not None and target_total <= 0:
        raise ValueError("target_total must be positive or None")

    if interval_type and interval_type not in ("daily", "weekly", "n_days"):
        raise ValueError("interval_type must be 'daily', 'weekly', 'n_days', or None")

    if interval_type == "weekly" and interval_value is not None:
        if not (0 <= interval_value <= 6):
            raise ValueError("weekly interval_value must be 0-6 (Sat-Fri)")

    if interval_type == "n_days" and interval_value is not None:
        if interval_value <= 0:
            raise ValueError("n_days interval_value must be positive")

    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO target_entries
                (kind, name, target_total, interval_type, interval_value, target_per_interval, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (kind, name, target_total, interval_type, interval_value, target_per_interval, int(time.time())),
        )
        conn.commit()
        return cur.lastrowid


def get_entry_by_name(name: str) -> dict | None:
    """Fetch an entry by its unique name."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM target_entries WHERE name = ?", (name,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_entry_by_id(entry_id: int) -> dict | None:
    """Fetch an entry by its ID."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM target_entries WHERE id = ?", (entry_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_all_entries(kind: str | None = None) -> list[dict]:
    """Fetch all entries, optionally filtered by kind."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        if kind:
            cur.execute("SELECT * FROM target_entries WHERE kind = ? ORDER BY name", (kind,))
        else:
            cur.execute("SELECT * FROM target_entries ORDER BY name")
        return [dict(row) for row in cur.fetchall()]


def record_progress(entry_id: int, amount: int, new_total: int, instance_date: str, logged_at: int) -> None:
    """Atomically append a progress log and update the entry's cached total."""
    with get_connection_cm(auto=False) as conn:
        conn.execute(
            "INSERT INTO target_logs (entry_id, amount, instance_date, logged_at) VALUES (?, ?, ?, ?)",
            (entry_id, amount, instance_date, logged_at),
        )
        conn.execute("UPDATE target_entries SET logged_total = ? WHERE id = ?", (new_total, entry_id))
        conn.commit()


def toggle_pause(entry_id: int, days: int | None = None) -> str:
    """
    Toggle pause for an entry.
    If paused, unpause. If not paused, pause for N days (default 1).
    Returns a confirmation string.
    """
    entry = get_entry_by_id(entry_id)
    if not entry:
        return f"Entry {entry_id} not found."

    today = clock.today()
    currently_paused = is_paused(entry, today)

    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()

        if currently_paused:
            # Unpause: clear paused_until
            cur.execute("UPDATE target_entries SET paused_until = NULL WHERE id = ?", (entry_id,))
            conn.commit()
            return f"Unpaused: {entry['name']}"
        else:
            # Pause for N days
            if days is None:
                days = 1
            pause_date = today + jdatetime.timedelta(days=days)
            cur.execute(
                "UPDATE target_entries SET paused_until = ? WHERE id = ?", (pause_date.strftime("%Y-%m-%d"), entry_id)
            )
            conn.commit()
            return f"Paused {entry['name']} until {pause_date.strftime('%Y-%m-%d')} ({days} days)"


def edit_entry(entry_id: int, **kwargs) -> str:
    """
    Edit fields of a target entry.
    Allowed fields: name, target_total, interval_type, interval_value, target_per_interval.
    Returns a confirmation string.
    """
    entry = get_entry_by_id(entry_id)
    if not entry:
        return f"Entry {entry_id} not found."

    allowed = {"name", "target_total", "interval_type", "interval_value", "target_per_interval"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}

    if not updates:
        return "No fields to update."

    # Validate target_total
    if "target_total" in updates and updates["target_total"] is not None:
        if updates["target_total"] <= 0:
            return "Target must be positive or None."

    # Validate interval_type
    if "interval_type" in updates and updates["interval_type"] is not None:
        if updates["interval_type"] not in ("daily", "weekly", "n_days"):
            return "interval_type must be 'daily', 'weekly', 'n_days', or None"

    # Validate interval_value
    if "interval_value" in updates and updates["interval_value"] is not None:
        iv = updates["interval_value"]
        itype = updates.get("interval_type", entry.get("interval_type"))
        if itype == "weekly" and not (0 <= iv <= 6):
            return "weekly interval_value must be 0-6 (Sat-Fri)"
        if itype == "n_days" and iv <= 0:
            return "n_days interval_value must be positive"

    # Build SQL
    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [entry_id]

    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE target_entries SET {set_clause} WHERE id = ?", values)
        conn.commit()

    return f"Updated: {entry['name']}"


def delete_entry(entry_id: int) -> str:
    """
    Delete a target entry and all its logs (cascade).
    Returns a confirmation string.
    """
    entry = get_entry_by_id(entry_id)
    if not entry:
        return f"Entry {entry_id} not found."

    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM target_entries WHERE id = ?", (entry_id,))
        conn.commit()

    return f"Deleted: {entry['name']}"
