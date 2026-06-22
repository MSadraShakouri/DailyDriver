# dailydriver/features/qada/_logic.py
"""Qada feature – prayer backlog logic."""

import time

from dailydriver.core.database import get_connection_cm
from dailydriver.utils.intervals import next_instance_date

VALID_PRAYER_SLOTS = ("fajr", "dhuhr_asr", "maghrib_isha")

# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------


def add_entry(name, kind, interval_type=None, interval_value=None, slot=None):
    """Insert a new qada entry. Returns the new entry ID."""
    if kind == "prayer":
        if slot not in VALID_PRAYER_SLOTS:
            raise ValueError(f"slot must be one of {VALID_PRAYER_SLOTS} for prayer entries")
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO qada_entries (name, kind, interval_type, interval_value, slot) VALUES (?,?,?,?,?)",
            (name, kind, interval_type, interval_value, slot),
        )
        conn.commit()
        return cur.lastrowid


def list_entries(kind=None):
    """Return all qada entries, optionally filtered by kind."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        if kind:
            cur.execute("SELECT * FROM qada_entries WHERE kind=? ORDER BY name", (kind,))
        else:
            cur.execute("SELECT * FROM qada_entries ORDER BY name")
        return [dict(row) for row in cur.fetchall()]


def log_prayer_qada(entry_id, amount, now=None):
    """Log a qada prayer entry. Returns a confirmation string."""
    if now is None:
        now = time.time()

    import jdatetime

    with get_connection_cm() as conn:
        cur = conn.cursor()
        today = jdatetime.date.today().strftime("%Y-%m-%d")
        cur.execute(
            "INSERT INTO qada_logs (entry_id, amount, instance_date, logged_at) VALUES (?,?,?,?)",
            (entry_id, amount, today, int(now)),
        )
        # Last write wins: delete any matching decline row
        cur.execute(
            "DELETE FROM qada_declines WHERE entry_id=? AND instance_date=?",
            (entry_id, today),
        )
        conn.commit()
        cur.execute("SELECT name FROM qada_entries WHERE id=?", (entry_id,))
        entry = cur.fetchone()
        name = entry["name"] if entry else str(entry_id)
        return f"Logged {amount} for {name}"


def compute_pending_instance(entry, today):
    """Return the pending instance date for *entry* on *today*, or None."""
    import jdatetime

    if _is_paused(entry, today):
        return None

    if not entry.get("interval_type"):
        return None

    # Find the most recent log or decline date
    last_log = _get_last_log_date(entry["id"])
    last_decline = _get_last_decline_date(entry["id"])
    last_fulfilled = last_log if last_log else None
    if last_decline and (last_fulfilled is None or last_decline > last_fulfilled):
        last_fulfilled = last_decline

    # Resolve reference date from created_at
    ref_str = entry.get("created_at")
    if ref_str:
        if isinstance(ref_str, int):
            ref_date = jdatetime.date.fromtimestamp(ref_str)
        else:
            ref_date = jdatetime.date(*map(int, str(ref_str).split("-")))
    else:
        ref_date = today

    next_date = next_instance_date(
        entry["interval_type"],
        entry.get("interval_value"),
        entry.get("interval_calendar", "jalali"),
        last_fulfilled,
        ref_date,
    )

    # --- amount-deferred scheduling (for qada prayers only) ---
    if next_date and entry["interval_type"] in ("n_days", "daily"):
        last_amount = _get_last_log_amount(entry["id"])
        if last_amount and last_amount > 1:
            # Determine the interval length in days
            if entry["interval_type"] == "n_days" and entry.get("interval_value"):
                ival = int(entry["interval_value"])
            else:
                ival = 1  # daily defaults to 1 day
            next_date = next_date + jdatetime.timedelta(days=(last_amount - 1) * ival)

    return next_date


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


def toggle_pause(entry_id, paused_from=None, paused_until=None):
    """Set or clear the pause range for an entry."""
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE qada_entries SET paused_from=?, paused_until=? WHERE id=?",
            (paused_from, paused_until, entry_id),
        )
        conn.commit()


def delete_entry(entry_id):
    """Delete a qada entry (logs and declines cascade)."""
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM qada_entries WHERE id=?", (entry_id,))
        conn.commit()


def edit_entry(entry_id, **kwargs):
    """Edit fields of a qada entry. Discards current instance per spec."""
    allowed = {"name", "interval_type", "interval_value", "interval_calendar"}
    updates = {k: v for k, v in kwargs.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [entry_id]
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute(f"UPDATE qada_entries SET {set_clause} WHERE id=?", values)
        conn.commit()


# ---------------------------------------------------------------------------
#  Internal helpers
# ---------------------------------------------------------------------------


def _get_last_log_date(entry_id):
    """Return the most recent instance_date from qada_logs for the entry, as a jdatetime.date or None."""
    import jdatetime

    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT instance_date FROM qada_logs WHERE entry_id=? ORDER BY instance_date DESC LIMIT 1",
            (entry_id,),
        )
        row = cur.fetchone()
        if row and row["instance_date"]:
            return jdatetime.date(*map(int, row["instance_date"].split("-")))
    return None


def _get_last_decline_date(entry_id):
    """Return the most recent instance_date from qada_declines for the entry, as a jdatetime.date or None."""
    import jdatetime

    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT instance_date FROM qada_declines WHERE entry_id=? ORDER BY instance_date DESC LIMIT 1",
            (entry_id,),
        )
        row = cur.fetchone()
        if row and row["instance_date"]:
            return jdatetime.date(*map(int, row["instance_date"].split("-")))
    return None


def _get_last_log_amount(entry_id):
    """Return the amount of the most recent log for the entry, or None."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT amount FROM qada_logs WHERE entry_id=? ORDER BY instance_date DESC LIMIT 1",
            (entry_id,),
        )
        row = cur.fetchone()
        return row["amount"] if row else None


def _is_paused(entry, today):
    """Return True if *entry* is paused on *today*."""
    paused_from = entry.get("paused_from")
    paused_until = entry.get("paused_until")
    if not paused_from:
        return False
    today_str = today.strftime("%Y-%m-%d") if hasattr(today, "strftime") else today
    if paused_from <= today_str:
        if paused_until is None or today_str <= paused_until:
            return True
    return False


# ---------------------------------------------------------------------------
#  Command parser
# ---------------------------------------------------------------------------


def qada_command(line: str):
    """Main entry point for the qada command."""
    parts = line.strip().split(maxsplit=2)
    if len(parts) == 1:  # bare "qada"
        return "Interactive qada manager is not yet implemented. Use 'qada log <name> <amount>' to log."

    sub = parts[1].lower()
    if sub == "log":
        return _parse_log(parts[2] if len(parts) > 2 else "")
    if sub == "fasting":
        return "Fasting commands will be available soon."
    return f"Unknown qada sub-command: {sub}"


def _parse_log(args_str):
    """Parse 'qada log <slot|id> [amount]' and execute."""
    tokens = args_str.strip().split()
    if not tokens:
        return "Usage: qada log <slot|id> [amount]"

    arg = tokens[0]
    amount = 1
    if len(tokens) > 1 and tokens[1].isdigit():
        amount = int(tokens[1])

    entry_id = resolve_entry_id(arg)
    if entry_id is None:
        return f"No qada entry found for '{arg}'."

    return log_prayer_qada(entry_id, amount)
