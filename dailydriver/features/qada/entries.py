"""Persistence and lifecycle operations for qada entries."""

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.features.presentation import is_paused

VALID_PRAYER_SLOTS = ("fajr", "dhuhr_asr", "maghrib_isha")


def add_entry(name, kind, interval_type=None, interval_value=None, slot=None, target_total=-1):
    """Insert a new qada entry. Returns the new entry ID."""
    if kind == "prayer":
        if slot not in VALID_PRAYER_SLOTS:
            raise ValueError(f"slot must be one of {VALID_PRAYER_SLOTS} for prayer entries")
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO qada_entries
               (name, kind, interval_type, interval_value, slot, target_total, logged_total)
               VALUES (?,?,?,?,?,?,?)""",
            (name, kind, interval_type, interval_value, slot, target_total, 0),
        )
        conn.commit()
        return cur.lastrowid


def get_entry_by_slot_or_kind(slot=None, kind=None):
    """Fetch an entry by slot (for prayer) or kind (for fasting)."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        if kind == "fasting":
            cur.execute("SELECT * FROM qada_entries WHERE kind='fasting' ORDER BY id LIMIT 1")
        elif kind == "prayer" and slot:
            cur.execute("SELECT * FROM qada_entries WHERE kind='prayer' AND slot=?", (slot,))
        else:
            return None
        row = cur.fetchone()
        return dict(row) if row else None


def list_entries(kind=None):
    """Return all qada entries, optionally filtered by kind."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        if kind:
            cur.execute("SELECT * FROM qada_entries WHERE kind=? ORDER BY name", (kind,))
        else:
            cur.execute("SELECT * FROM qada_entries ORDER BY name")
        return [dict(row) for row in cur.fetchall()]


def resolve_entry_id(arg):
    """Resolve a command-line argument to an entry ID.
    Numeric → direct ID lookup.
    Otherwise: try slot lookup (for prayer entries), then fall back to name.
    Returns the entry ID or None."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        if arg.isdigit():
            cur.execute("SELECT id FROM qada_entries WHERE id=?", (int(arg),))
        else:
            # Try slot lookup first (for prayer entries)
            slot_candidate = arg.lower().replace(" ", "_")
            if slot_candidate in VALID_PRAYER_SLOTS:
                cur.execute("SELECT id FROM qada_entries WHERE kind='prayer' AND slot=?", (slot_candidate,))
                row = cur.fetchone()
                if row:
                    return row["id"]
            # Fall back to name lookup
            cur.execute("SELECT id FROM qada_entries WHERE name=?", (arg,))
        row = cur.fetchone()
        return row["id"] if row else None


def get_entry(entry_id):
    """Fetch a single qada entry by ID. Returns dict or None."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM qada_entries WHERE id=?", (entry_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def toggle_pause(entry_id, days: int = 1) -> str:
    """Toggle pause: if paused, resume; else pause for `days`."""
    entry = get_entry(entry_id)
    if not entry:
        return f"Entry {entry_id} not found."

    today = jdatetime.date.today()
    currently_paused = is_paused(entry, today)

    with get_connection_cm() as conn:
        cur = conn.cursor()
        if currently_paused:
            # Unpause: clear paused_until
            cur.execute("UPDATE qada_entries SET paused_until = NULL WHERE id = ?", (entry_id,))
            conn.commit()
            return f"Unpaused {entry['name']}"
        else:
            # Pause for N days
            pause_date = today + jdatetime.timedelta(days=days)
            cur.execute(
                "UPDATE qada_entries SET paused_until = ? WHERE id = ?",
                (pause_date.strftime("%Y-%m-%d"), entry_id),
            )
            conn.commit()
            return f"Paused {entry['name']} until {pause_date.strftime('%Y-%m-%d')} ({days} days)"


def delete_entry(entry_id):
    """Delete a qada entry (logs and declines cascade)."""
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM qada_entries WHERE id=?", (entry_id,))
        conn.commit()


def edit_entry(entry_id, **kwargs):
    """Edit fields of a qada entry. Handles target changes with proper logic."""
    allowed = {"name", "interval_type", "interval_value", "interval_calendar", "target_total", "paused_until"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}

    if not updates:
        return

    # Handle target_total changes
    if "target_total" in updates:
        new_target = updates["target_total"]
        with get_connection_cm(auto=False) as conn:
            cur = conn.cursor()
            cur.execute("SELECT target_total, logged_total FROM qada_entries WHERE id=?", (entry_id,))
            row = cur.fetchone()
            if row:
                old_target = row["target_total"]
                logged = row["logged_total"]

                if old_target == -1:
                    # Entry was not set, just set the target
                    pass
                elif new_target > old_target:
                    # Higher target: keep logged_total as-is
                    pass
                elif new_target < old_target:
                    # Lower target: warn, then cap if needed
                    if logged > new_target:
                        updates["logged_total"] = new_target

    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [entry_id]
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE qada_entries SET {set_clause} WHERE id=?", values)
        conn.commit()
