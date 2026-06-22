# dailydriver/features/qada/_header.py
"""Qada prayer header nudges."""

from datetime import datetime, timedelta

import jdatetime

from dailydriver.features.qada._logic import compute_pending_instance, list_entries
from dailydriver.utils.prayer_times import get_approximate_times


def get_prayer_nudges(conn, target_date, now=None):
    """Return nudge lines for qada prayer entries with a pending instance today.
    Only shows if within 1 hour before prayer time.
    Shows: '🕌 Fajr: not set' if target=-1 and pending today.
           '🕌 Fajr pending' if target>0, logged<target, pending today.
    Hides if complete, paused, or no pending instance."""
    if now is None:
        now = datetime.now()

    today_j = jdatetime.date.today()

    if target_date != today_j:
        return []

    entries = list_entries(kind="prayer")
    nudges = []

    for entry in entries:
        # Check paused
        paused_until = entry.get("paused_until")
        if paused_until:
            try:
                y, m, d = map(int, paused_until.split("-"))
                pause_date = jdatetime.date(y, m, d)
                if pause_date >= today_j:
                    continue
            except (ValueError, TypeError):
                pass

        # Need interval to be scheduled
        if not entry.get("interval_type"):
            continue

        target = entry.get("target_total", -1)
        logged = entry.get("logged_total", 0)

        # Compute pending instance
        pending = compute_pending_instance(entry, today_j)
        if pending != today_j:
            continue

        # Get prayer time and check window
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
        if now < prayer_dt - timedelta(hours=1):
            continue

        # Not set
        if target == -1:
            display = slot_name.replace("_", "/").title()
            nudges.append(f"🕌 {display}: not set")
            continue

        # Complete
        if target > 0 and logged >= target:
            continue

        # Pending
        display = slot_name.replace("_", "/").title()
        nudges.append(f"🕌 {display} pending")

    return nudges


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
        # Check paused
        paused_until = entry.get("paused_until")
        if paused_until:
            try:
                y, m, d = map(int, paused_until.split("-"))
                pause_date = jdatetime.date(y, m, d)
                if pause_date >= today_j:
                    continue
            except (ValueError, TypeError):
                pass

        # Need interval to be scheduled
        if not entry.get("interval_type"):
            continue

        target = entry.get("target_total", -1)
        logged = entry.get("logged_total", 0)

        # Compute pending instance
        pending = compute_pending_instance(entry, target_date)
        if pending is None:
            continue

        # If pending is before today, auto-no
        if pending < target_date:
            day = pending
            while day < target_date:
                day_str = day.strftime("%Y-%m-%d")
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
                cur.execute(
                    "INSERT OR IGNORE INTO qada_declines (entry_id, instance_date, logged_at) VALUES (?,?,?)",
                    (entry["id"], day_str, int(now.timestamp())),
                )
                day += jdatetime.timedelta(days=1)
            conn.commit()
            continue

        # If pending is after today, no nudge yet
        if pending > target_date:
            continue

        # pending == today: check if already responded
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

        # Not set
        if target == -1:
            nudges.append("🌙 Fasting: not set")
            continue

        # Complete
        if target > 0 and logged >= target:
            continue

        # Pending
        nudges.append("🌙 Fasting pending")

    return nudges
