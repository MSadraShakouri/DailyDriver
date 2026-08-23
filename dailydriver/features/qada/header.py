"""Qada prayer header nudges."""

from datetime import datetime, timedelta

import jdatetime

from dailydriver.core.state import is_travel_mode
from dailydriver.features.presentation import is_paused
from dailydriver.utils.prayer_times import get_approximate_times

from .entries import list_entries
from .schedule import compute_pending_instance, get_current_pending_instance


def get_prayer_nudges(conn, target_date, now=None):
    """Return nudge lines for qada prayer entries with a pending instance today.
    Only shows if within 1 hour before prayer time.
    Shows: '🕌 Fajr: not set' if target=-1 and pending today.
           '🕌 Fajr pending' if target>0, logged<target, pending today.
    Hides if complete, paused, or no pending instance."""

    if is_travel_mode():
        return []
    if now is None:
        now = datetime.now()

    today_j = jdatetime.date.today()
    if target_date != today_j:
        return []

    entries = list_entries(kind="prayer")
    nudges = []  # list of (pending_date, line)

    for entry in entries:
        # Skip paused (handled in get_current_pending_instance)
        # Skip if no interval
        if not entry.get("interval_type"):
            continue

        pending = get_current_pending_instance(entry, today_j)
        if pending is None:
            continue

        # Get prayer time for this slot
        slot_name = entry.get("slot")
        if slot_name is None:
            continue
        approx = get_approximate_times(today_j.month, today_j.day)
        slot_map = {
            "fajr": "fajr",
            "dhuhr_asr": "dhuhr",
            "maghrib_isha": "maghrib",
        }
        approx_key = slot_map.get(slot_name)
        if approx_key is None:
            continue
        hour, minute = approx[approx_key]
        prayer_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Determine if overdue or due today
        if pending < today_j:
            # Overdue – always show
            display = slot_name.replace("_", "/").title()
            nudges.append((pending, f"🕌 {display} overdue!"))
        elif pending == today_j:
            # Due today – only show in the hour before prayer
            if now >= prayer_dt - timedelta(hours=1):
                target = entry.get("target_total", -1)
                logged = entry.get("logged_total", 0)
                if target == -1:
                    display = slot_name.replace("_", "/").title()
                    nudges.append((pending, f"🕌 {display} not set"))
                elif logged < target:
                    display = slot_name.replace("_", "/").title()
                    nudges.append((pending, f"🕌 {display} pending"))

    # Sort by pending_date (chronological, oldest first)
    nudges.sort(key=lambda x: x[0])
    return [line for _, line in nudges]


def get_fasting_nudges(conn, target_date, now=None):
    """Return fasting nudge lines for today's pending instances.
    Shows: '🌙 Fasting: not set' if target=-1 and pending today.
           '🌙 Fasting pending' if target>0, logged<target, pending today.
    Hides if complete, paused, or no pending instance.
    Also handles lazy auto-no: writes decline rows for missed days."""
    if now is None:
        now = datetime.now()

    today_j = jdatetime.date.today()
    if target_date != today_j:
        return []

    entries = list_entries(kind="fasting")
    nudges = []

    for entry in entries:
        # Skip paused entries (using new _is_paused)
        if is_paused(entry, today_j):
            continue

        # Need interval to be scheduled
        if not entry.get("interval_type"):
            continue

        target = entry.get("target_total", -1)
        logged = entry.get("logged_total", 0)

        # Compute pending instance
        pending = compute_pending_instance(entry, target_date)
        if pending is None:
            continue

        # If pending is in the past → overdue
        if pending < target_date:
            nudges.append("🌙 Fasting overdue!")
            continue

        # If pending is today → pending
        if pending == target_date:
            # Check if already responded (log exists)
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM qada_logs WHERE entry_id=? AND instance_date=?",
                (entry["id"], target_date.strftime("%Y-%m-%d")),
            )
            if cur.fetchone():
                continue
            # Not set or pending
            if target == -1:
                nudges.append("🌙 Fasting: not set")
            elif target > 0 and logged >= target:
                continue  # complete
            else:
                nudges.append("🌙 Fasting pending")

        # If pending > today, skip (too early)

    return nudges
