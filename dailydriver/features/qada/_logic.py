# dailydriver/features/qada/_logic.py
"""Qada feature – prayer backlog logic."""

import time

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.utils.intervals import next_instance_date

VALID_PRAYER_SLOTS = ("fajr", "dhuhr_asr", "maghrib_isha")

# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------


def add_entry(name, kind, interval_type=None, interval_value=None, slot=None, target_total=-1):
    """Insert a new qada entry. Returns the new entry ID."""
    if kind == "prayer":
        if slot not in VALID_PRAYER_SLOTS:
            raise ValueError(f"slot must be one of {VALID_PRAYER_SLOTS} for prayer entries")
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO qada_entries (name, kind, interval_type, interval_value, slot, target_total, logged_total) VALUES (?,?,?,?,?,?,?)",
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


def get_all_entries_with_progress(today=None):
    """Return all 4 qada entries in fixed order with progress computed."""
    if today is None:
        today = jdatetime.date.today()

    # Define the 4 entries
    entry_defs = [
        {"slot": "fajr", "kind": "prayer", "name": "Fajr"},
        {"slot": "dhuhr_asr", "kind": "prayer", "name": "Dhuhr/Asr"},
        {"slot": "maghrib_isha", "kind": "prayer", "name": "Maghrib/Isha"},
        {"slot": None, "kind": "fasting", "name": "Fasting"},
    ]

    result = []
    for idx, defn in enumerate(entry_defs, 1):
        entry = get_entry_by_slot_or_kind(slot=defn["slot"], kind=defn["kind"])
        if entry is None:
            # Create with defaults
            name = defn["name"]
            entry_id = add_entry(
                name=name,
                kind=defn["kind"],
                slot=defn["slot"],
                interval_type="daily",
                target_total=-1,
            )
            entry = get_entry_by_slot_or_kind(slot=defn["slot"], kind=defn["kind"])
            if entry is None:
                # Fallback: shouldn't happen
                continue

        # Compute progress
        target = entry.get("target_total", -1)
        logged = entry.get("logged_total", 0)
        if target == -1:
            progress_display = "Not set"
            percentage = None
            is_complete = False
        elif target == 0:
            progress_display = "0/0"
            percentage = "0.000%"
            is_complete = True
        else:
            pct = (logged / target) * 100
            percentage = f"{pct:.3f}%"
            progress_display = f"{logged}/{target}"
            is_complete = logged >= target

        # Check paused
        paused_until = entry.get("paused_until")
        is_paused = False
        if paused_until:
            try:
                y, m, d = map(int, paused_until.split("-"))
                pause_date = jdatetime.date(y, m, d)
                is_paused = pause_date >= today
            except (ValueError, TypeError):
                pass

        # Compute next instance
        next_instance = None
        if not is_complete and target > 0 and not is_paused:
            next_instance = compute_pending_instance(entry, today)

        result.append(
            {
                "id": entry["id"],
                "index": idx,
                "name": defn["name"],
                "kind": defn["kind"],
                "slot": defn["slot"],
                "target_total": target,
                "logged_total": logged,
                "progress_display": progress_display,
                "percentage": percentage,
                "is_complete": is_complete,
                "is_paused": is_paused,
                "next_instance": next_instance,
                "interval_type": entry.get("interval_type"),
                "interval_value": entry.get("interval_value"),
                "paused_until": paused_until,
            }
        )

    return result


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

        # Get current logged total and target
        cur.execute("SELECT logged_total, target_total FROM qada_entries WHERE id=?", (entry_id,))
        row = cur.fetchone()
        if not row:
            return "Entry not found."

        logged = row["logged_total"]
        target = row["target_total"]

        if target <= 0:
            return "Target is not set or complete. Nothing to log."

        # Cap amount at target
        if logged + amount > target:
            amount = target - logged

        if amount <= 0:
            return "Already at target. Nothing to log."

        # Insert log
        cur.execute(
            "INSERT INTO qada_logs (entry_id, amount, instance_date, logged_at) VALUES (?,?,?,?)",
            (entry_id, amount, today, int(now)),
        )
        # Update logged_total
        cur.execute(
            "UPDATE qada_entries SET logged_total = logged_total + ? WHERE id=?",
            (amount, entry_id),
        )
        conn.commit()

        # Get updated totals
        cur.execute("SELECT logged_total, target_total FROM qada_entries WHERE id=?", (entry_id,))
        row = cur.fetchone()
        new_logged = row["logged_total"]
        new_target = row["target_total"]
        pct = (new_logged / new_target) * 100

        cur.execute("SELECT name FROM qada_entries WHERE id=?", (entry_id,))
        entry = cur.fetchone()
        name = entry["name"] if entry else str(entry_id)

        return f"{name}: {new_logged}/{new_target} ({pct:.3f}%)"


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


def log_fasting(entry_id, now=None):
    """Log a fasting entry for today. Returns confirmation string.
    Fails if a decline already exists for today (no is final)."""
    if now is None:
        now = time.time()

    import jdatetime

    today = jdatetime.date.today().strftime("%Y-%m-%d")

    with get_connection_cm() as conn:
        cur = conn.cursor()

        # Check if decline exists for today
        cur.execute(
            "SELECT 1 FROM qada_declines WHERE entry_id=? AND instance_date=?",
            (entry_id, today),
        )
        if cur.fetchone():
            conn.commit()
            return "Cannot log: you already declined today. Use the manager to edit."

        # Get current logged total and target
        cur.execute("SELECT logged_total, target_total FROM qada_entries WHERE id=?", (entry_id,))
        row = cur.fetchone()
        if not row:
            return "Entry not found."

        logged = row["logged_total"]
        target = row["target_total"]

        if target <= 0:
            return "Target is not set or complete. Nothing to log."

        # Cap amount at target
        amount = 1
        if logged + amount > target:
            amount = target - logged

        if amount <= 0:
            return "Already at target. Nothing to log."

        # Insert log
        cur.execute(
            "INSERT INTO qada_logs (entry_id, amount, instance_date, logged_at) VALUES (?,?,?,?)",
            (entry_id, amount, today, int(now)),
        )
        # Update logged_total
        cur.execute(
            "UPDATE qada_entries SET logged_total = logged_total + ? WHERE id=?",
            (amount, entry_id),
        )
        conn.commit()

        cur.execute("SELECT logged_total, target_total FROM qada_entries WHERE id=?", (entry_id,))
        row = cur.fetchone()
        new_logged = row["logged_total"]
        new_target = row["target_total"]
        pct = (new_logged / new_target) * 100

        cur.execute("SELECT name FROM qada_entries WHERE id=?", (entry_id,))
        entry = cur.fetchone()
        name = entry["name"] if entry else str(entry_id)

        return f"{name}: {new_logged}/{new_target} ({pct:.3f}%)"


def decline_fasting(entry_id, now=None):
    """Decline a fasting entry for today (no). Returns confirmation string."""
    if now is None:
        now = time.time()

    import jdatetime

    today = jdatetime.date.today().strftime("%Y-%m-%d")

    with get_connection_cm() as conn:
        cur = conn.cursor()

        # Insert decline (idempotent)
        cur.execute(
            "INSERT OR IGNORE INTO qada_declines (entry_id, instance_date, logged_at) VALUES (?,?,?)",
            (entry_id, today, int(now)),
        )
        conn.commit()

        cur.execute("SELECT name FROM qada_entries WHERE id=?", (entry_id,))
        entry = cur.fetchone()
        name = entry["name"] if entry else str(entry_id)
        return f"Fasting declined for {name}"


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
    if len(parts) == 1:
        # Bare qada → open manager
        from dailydriver.features.qada import _manager

        _manager.show_qada_manager()
        return None

    sub = parts[1].lower()
    if sub == "log":
        return _parse_log(parts[2] if len(parts) > 2 else "")
    if sub == "fasting":
        return _parse_fasting(parts[2] if len(parts) > 2 else "")
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


def _parse_fasting(args_str):
    """Parse 'qada fasting yes|no' and execute."""
    tokens = args_str.strip().split()
    if not tokens or tokens[0] not in ("yes", "no"):
        return "Usage: qada fasting yes | qada fasting no"

    response = tokens[0]

    # Find the single fasting entry
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM qada_entries WHERE kind='fasting' ORDER BY id LIMIT 1")
        row = cur.fetchone()
        if not row:
            return "No fasting entry found. Add one first."

    entry_id = row["id"]

    if response == "yes":
        return log_fasting(entry_id)
    else:  # "no"
        return decline_fasting(entry_id)
