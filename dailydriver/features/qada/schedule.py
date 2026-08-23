"""Qada recurrence and pending-instance calculations."""

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.features.presentation import is_paused
from dailydriver.utils.intervals import next_instance_date


def _get_last_log_date(entry_id):
    """Return the most recent instance_date from qada_logs for the entry."""
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


def _is_instance_logged(entry_id, instance_date):
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM qada_logs WHERE entry_id=? AND instance_date=?",
            (entry_id, instance_date.strftime("%Y-%m-%d")),
        )
        return cur.fetchone() is not None


def compute_pending_instance(entry, today):
    """Return the pending instance date for *entry* on *today*, or None."""
    # 1. Check pause
    if is_paused(entry, today):
        return None

    # 2. Get the most recent log date
    last_log = _get_last_log_date(entry["id"])
    if last_log is not None:
        # There is a log – the next instance is after the last log
        ref_date = last_log
        last_fulfilled = last_log
    else:
        # No logs yet – start from today
        ref_date = today
        last_fulfilled = None

    # 3. Compute next instance
    return next_instance_date(
        entry["interval_type"],
        entry.get("interval_value"),
        entry.get("interval_calendar", "jalali"),
        last_fulfilled,
        ref_date,
    )


def get_current_pending_instance(entry, today):
    """
    Return the earliest scheduled instance date <= today that is NOT logged.
    If none (all instances up to today are logged, or entry is paused/complete), return None.
    """
    # Check if target is reached
    target = entry.get("target_total", -1)
    logged = entry.get("logged_total", 0)
    if target != -1 and logged >= target:
        return None

    # Check pause
    if is_paused(entry, today):
        return None

    # Determine starting point
    # If there is a last log, start from the day after that log
    last_log = _get_last_log_date(entry["id"])
    if last_log is not None:
        # start from the day after last_log
        ref_date = last_log + jdatetime.timedelta(days=1)
        last_fulfilled = last_log
    else:
        # No logs: start from the entry's creation date (or today minus a year as fallback)
        created_at = entry.get("created_at")
        if created_at:
            ref_date = jdatetime.date.fromtimestamp(created_at)
        else:
            ref_date = today - jdatetime.timedelta(days=365)  # far past
        last_fulfilled = None

    # Iterate forward until we exceed today
    max_scan = 365  # safety
    for _ in range(max_scan):
        instance = next_instance_date(
            entry["interval_type"],
            entry.get("interval_value"),
            entry.get("interval_calendar", "jalali"),
            last_fulfilled,
            ref_date,
        )
        if instance is None or instance > today:
            break
        # Check if this instance is logged
        if not _is_instance_logged(entry["id"], instance):
            return instance
        # It's logged, move forward
        last_fulfilled = instance
        ref_date = instance + jdatetime.timedelta(days=1)

    return None
