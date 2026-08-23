"""Progress logging for qada prayers and fasting."""

import time

import jdatetime

from dailydriver.core.database import get_connection_cm

from .entries import get_entry, toggle_pause
from .schedule import compute_pending_instance


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


def log_fasting(entry_id, now=None):
    """Log a fasting entry for today's pending instance. Returns confirmation string.
    Fails if a decline already exists for today (no is final).
    Uses the pending instance date (not hardcoded today)."""
    if now is None:
        now = time.time()

    import jdatetime

    today_j = jdatetime.date.today()
    today_str = today_j.strftime("%Y-%m-%d")

    with get_connection_cm() as conn:
        cur = conn.cursor()

        # Get the entry
        cur.execute("SELECT * FROM qada_entries WHERE id=?", (entry_id,))
        row = cur.fetchone()
        if not row:
            return "Entry not found."
        entry = dict(row)

        # Compute pending instance (for display only – we don't use it for the log)
        pending = compute_pending_instance(entry, today_j)
        if pending is None:
            return "No pending fasting instance."

        # Always log against today's date. The pending date is for display only.
        instance_date = today_str

        # Check if there's already a log or decline for that instance date
        cur.execute(
            "SELECT 1 FROM qada_logs WHERE entry_id=? AND instance_date=?",
            (entry_id, instance_date),
        )
        if cur.fetchone():
            return f"Already logged for {instance_date}."

        logged = entry.get("logged_total", 0)
        target = entry.get("target_total", -1)

        if target == 0:
            return "Target is 0. Nothing to log."

        amount = 1
        if target != -1 and logged + amount > target:
            amount = target - logged
            if amount <= 0:
                return "Already at target. Nothing to log."

        # Insert log
        cur.execute(
            "INSERT INTO qada_logs (entry_id, amount, instance_date, logged_at) VALUES (?,?,?,?)",
            (entry_id, amount, instance_date, int(now)),
        )
        cur.execute(
            "UPDATE qada_entries SET logged_total = logged_total + ? WHERE id=?",
            (amount, entry_id),
        )
        conn.commit()

    # Get updated totals for confirmation
    entry = get_entry(entry_id)
    new_logged = entry["logged_total"]
    new_target = entry["target_total"]

    if new_target == -1:
        pct = "∞"
        display = f"{new_logged}/∞"
    else:
        pct = f"{(new_logged / new_target) * 100:.3f}%"
        display = f"{new_logged}/{new_target}"

    name = entry.get("slot") if entry["kind"] == "prayer" else "Fasting"
    return f"{name}: {display} ({pct})"


def pause_fasting_entry() -> str:
    """Pause the fasting entry for 1 day."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM qada_entries WHERE kind='fasting' ORDER BY id LIMIT 1")
        row = cur.fetchone()
    if not row:
        return "No fasting entry found."
    return toggle_pause(row["id"], days=1)
