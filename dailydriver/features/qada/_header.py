# dailydriver/features/qada/_header.py
"""Qada prayer header nudges."""

from datetime import datetime

import jdatetime

from dailydriver.features.qada._logic import compute_pending_instance, list_entries
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


def get_fasting_nudges(conn, target_date, now=None):
    """Return fasting nudge lines for today's pending instances.
    Also handles lazy auto-no: writes decline rows for missed days."""
    if now is None:
        now = datetime.now()

    today_j = jdatetime.date.today()

    # Only show nudges for today
    if target_date != today_j:
        return []

    entries = list_entries(kind="fasting")
    nudges = []

    for entry in entries:
        # Only entries with an interval get nudges
        if not entry.get("interval_type"):
            continue

        # Compute pending instance
        pending = compute_pending_instance(entry, target_date)
        if pending is None:
            continue

        # If pending is before today, we missed days → auto-no
        if pending < target_date:
            # Process all missed days from pending to yesterday
            day = pending
            while day < target_date:
                day_str = day.strftime("%Y-%m-%d")

                # Check if already logged or declined
                cur = conn.cursor()
                cur.execute(
                    "SELECT 1 FROM qada_logs WHERE entry_id=? AND instance_date=?",
                    (entry["id"], day_str),
                )
                if cur.fetchone():
                    day += jdatetime.timedelta(days=1)
                    continue

                cur.execute(
                    "SELECT 1 FROM qada_declines WHERE entry_id=? AND instance_date=?",
                    (entry["id"], day_str),
                )
                if cur.fetchone():
                    day += jdatetime.timedelta(days=1)
                    continue

                # Auto-decline: insert decline row
                cur.execute(
                    "INSERT OR IGNORE INTO qada_declines (entry_id, instance_date, logged_at) VALUES (?,?,?)",
                    (entry["id"], day_str, int(now.timestamp())),
                )
                day += jdatetime.timedelta(days=1)

            # After processing missed days, skip this entry (no nudge)
            continue

        # If pending is after today, no nudge yet
        if pending > target_date:
            continue

        # pending == target_date: check if already responded
        cur = conn.cursor()
        cur.execute(
            "SELECT 1 FROM qada_logs WHERE entry_id=? AND instance_date=?",
            (entry["id"], target_date.strftime("%Y-%m-%d")),
        )
        if cur.fetchone():
            continue

        cur.execute(
            "SELECT 1 FROM qada_declines WHERE entry_id=? AND instance_date=?",
            (entry["id"], target_date.strftime("%Y-%m-%d")),
        )
        if cur.fetchone():
            continue

        # Show nudge
        nudges.append(f"🌙 {entry['name']} fasting pending — log with 'qada fasting yes' or 'qada fasting no'")

    return nudges
