# dailydriver/features/qada/_header.py
"""Qada prayer header nudges."""

from datetime import datetime

import jdatetime

from dailydriver.features.qada._logic import VALID_PRAYER_SLOTS, compute_pending_instance, list_entries
from dailydriver.utils.prayer_times import get_approximate_times


def get_prayer_nudges(conn, target_date, now=None):
    """Return a list of nudge lines for qada prayer entries with a pending instance today."""
    if now is None:
        now = datetime.now()

    today_j = jdatetime.date.today()
    approx = get_approximate_times(today_j.month, today_j.day)

    # Map prayer slot names to their prayer times
    prayer_times = {
        "fajr": (approx["fajr"][0], approx["fajr"][1]),
        "dhuhr_asr": (approx["dhuhr"][0], approx["dhuhr"][1]),
        "maghrib_isha": (approx["maghrib"][0], approx["maghrib"][1]),
    }

    entries = list_entries(kind="prayer")
    nudges = []

    for entry in entries:
        # Only entries with an interval get nudges
        if not entry.get("interval_type"):
            continue

        # Check if there is a pending instance today
        pending = compute_pending_instance(entry, today_j)
        if pending != today_j:
            continue

        # Determine the prayer time for this slot
        slot_name = entry.get("slot")
        if slot_name is None or slot_name not in prayer_times:
            continue  # skip misnamed or legacy entries

        hour, minute = prayer_times[slot_name]
        prayer_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        # Nudge window: 1 hour before prayer time until fulfilled
        if now >= prayer_dt - jdatetime.timedelta(hours=1):
            nudges.append(f"🕌 {entry['name']} qada pending — log with 'qada log {entry['name']} 1'")

    return nudges
