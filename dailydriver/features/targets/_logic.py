"""Core logic for targets feature."""

import time
from datetime import datetime

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.core.day_start import get_shifted_today
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.intervals import next_instance_date

from ._utils import get_counter_value, get_daily_total, get_last_fulfilled_date, set_counter_value


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
            INSERT INTO target_entries (kind, name, target_total, interval_type, interval_value, target_per_interval, created_at)
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


def get_last_fulfilled_date_for_entry(entry_id: int) -> jdatetime.date | None:
    """Wrapper for _utils.get_last_fulfilled_date."""
    return get_last_fulfilled_date(entry_id)


def get_daily_total_for_entry(entry_id: int, date: jdatetime.date) -> int:
    """Wrapper for _utils.get_daily_total."""
    return get_daily_total(entry_id, date)


def compute_next_due(entry: dict, today: jdatetime.date, conn=None) -> jdatetime.date | None:
    """Compute the next due date for an entry based on its interval and last fulfilled date."""
    if entry.get("paused_until"):
        try:
            y, m, d = map(int, entry["paused_until"].split("-"))
            pause_date = jdatetime.date(y, m, d)
            if pause_date >= today:
                return None
        except (ValueError, TypeError):
            pass

    if not entry.get("interval_type"):
        return None

    # Pass connection if available
    last_fulfilled = get_last_fulfilled_date(entry["id"], conn=conn)
    if last_fulfilled is None and entry.get("created_at"):
        ref_date = jdatetime.date.fromtimestamp(entry["created_at"])
    else:
        ref_date = today

    return next_instance_date(
        interval_type=entry["interval_type"],
        interval_value=str(entry["interval_value"]) if entry.get("interval_value") is not None else None,
        calendar="jalali",
        last_fulfilled_date=last_fulfilled,
        reference_date=ref_date,
    )


def log_progress(name: str, amount: int, expected_kind: str | None = None) -> str:
    """Log progress for an entry by name.
    If expected_kind is set, it validates the entry kind matches.
    Returns a confirmation string.
    """
    if amount <= 0:
        return "Amount must be positive."

    entry = get_entry_by_name(name)
    if not entry:
        return f"Entry not found: {name}"

    if expected_kind and entry["kind"] != expected_kind:
        return f"'{name}' is a {entry['kind']}, not a {expected_kind}."

    today = get_shifted_today()
    entry_id = entry["id"]
    target = entry["target_total"]
    current_logged = entry["logged_total"]

    # Calculate new total (cap at target if finite)
    new_total = current_logged + amount
    if target is not None and new_total > target:
        new_total = target

    actual_amount = new_total - current_logged
    if actual_amount <= 0:
        return "Already at target. Nothing to log."

    # Insert log
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO target_logs (entry_id, amount, instance_date, logged_at) VALUES (?, ?, ?, ?)",
            (entry_id, actual_amount, today.strftime("%Y-%m-%d"), int(time.time())),
        )
        cur.execute(
            "UPDATE target_entries SET logged_total = ? WHERE id = ?",
            (new_total, entry_id),
        )
        conn.commit()

    # Build confirmation
    total_display = f"{new_total}/{target}" if target is not None else f"{new_total}/∞"
    if target is not None and target > 0:
        pct = (new_total / target) * 100
        return f"{name}: {total_display} ({pct:.1f}%)"
    else:
        return f"{name}: {total_display}"


def handle_log_command(args: str, kind: str | None = None) -> str:
    """Handle 'nazr log' or 'habit log' commands.
    kind: 'nazr' or 'habit' to validate the entry kind.
    Returns a confirmation string or an error message.
    """
    parts = args.strip().split()
    if len(parts) < 2:
        return "Usage: log <name> <amount>"
    name, amount_str = parts[0], parts[1]
    try:
        amount = int(amount_str)
    except ValueError:
        return "Amount must be a number."
    if amount <= 0:
        return "Amount must be positive."
    return log_progress(name, amount, expected_kind=kind)


# ========== Pause, Edit, Delete ==========


def toggle_pause(entry_id: int, days: int | None = None) -> str:
    """
    Toggle pause for an entry.
    If paused, unpause. If not paused, pause for N days (default 1).
    Returns a confirmation string.
    """
    entry = get_entry_by_id(entry_id)
    if not entry:
        return f"Entry {entry_id} not found."

    today = get_shifted_today()
    paused_until = entry.get("paused_until")

    # Check if currently paused
    is_paused = False
    if paused_until:
        try:
            y, m, d = map(int, paused_until.split("-"))
            pause_date = jdatetime.date(y, m, d)
            if pause_date >= today:
                is_paused = True
        except (ValueError, TypeError):
            pass

    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()

        if is_paused:
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


def handle_daily_total(args: str, kind: str | None = None) -> str:
    """
    Usage: nazr daily_total <name> <total>
           habit daily_total <name> <total>
    Logs the difference between total and what's already logged today.
    """
    parts = args.strip().split()
    if len(parts) != 2:
        return "Usage: daily_total <name> <total>"
    name, total_str = parts[0], parts[1]
    try:
        total = int(total_str)
    except ValueError:
        return "Total must be a number."

    entry = get_entry_by_name(name)
    if not entry:
        return f"Entry not found: {name}"
    if kind and entry["kind"] != kind:
        return f"'{name}' is a {entry['kind']}, not a {kind}."

    today = get_shifted_today()
    today_total = get_daily_total(entry["id"], today)
    diff = total - today_total
    if diff == 0:
        return "No change. Nothing logged."
    if diff < 0:
        current_ui.print_line(f"Warning: Total {total} is less than today's logged total ({today_total}).")
        return "Negative amount not logged. Please adjust manually."
    return log_progress(name, diff, kind)


def handle_counter_total(args: str, kind: str | None = None) -> str:
    """
    Usage: nazr counter_total <name> <value>
           habit counter_total <name> <value>
    Logs the difference between value and the stored counter value.
    Updates the stored counter value after logging.
    """
    parts = args.strip().split()
    if len(parts) != 2:
        return "Usage: counter_total <name> <value>"
    name, value_str = parts[0], parts[1]
    try:
        value = int(value_str)
    except ValueError:
        return "Value must be a number."

    entry = get_entry_by_name(name)
    if not entry:
        return f"Entry not found: {name}"
    if kind and entry["kind"] != kind:
        return f"'{name}' is a {entry['kind']}, not a {kind}."

    last = get_counter_value(entry["id"])
    diff = value - last
    if diff == 0:
        return "No change. Nothing logged."
    if diff < 0:
        current_ui.print_line(f"Warning: Counter value {value} is less than previous value ({last}).")
        return "Negative amount not logged. Please adjust manually."

    set_counter_value(entry["id"], value)
    return log_progress(name, diff, kind)


def handle_counter_reset(args: str, kind: str | None = None) -> str:
    """
    Usage: nazr counter_reset <name>
           habit counter_reset <name>
    Resets the stored counter value to 0. Does not log anything.
    """
    parts = args.strip().split()
    if len(parts) != 1:
        return "Usage: counter_reset <name>"
    name = parts[0]

    entry = get_entry_by_name(name)
    if not entry:
        return f"Entry not found: {name}"
    if kind and entry["kind"] != kind:
        return f"'{name}' is a {entry['kind']}, not a {kind}."

    set_counter_value(entry["id"], 0)
    return f"Counter reset to 0 for {name}"
