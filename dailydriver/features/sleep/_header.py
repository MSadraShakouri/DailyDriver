# dailydriver/display/header/sleep.py
"""Sleep and nap header lines."""

from datetime import datetime


def get_sleep_str(conn, today):
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT sleep_time, wake_time, duration_minutes FROM sleep_logs WHERE jalali_date=? ORDER BY sleep_time",
        (today,),
    ).fetchall()
    if not rows:
        return "💤 —"

    total_duration = sum(r["duration_minutes"] for r in rows if r["duration_minutes"])
    ranges = []
    for r in rows:
        start = datetime.fromtimestamp(r["sleep_time"]).strftime("%H:%M")
        end = datetime.fromtimestamp(r["wake_time"]).strftime("%H:%M")
        ranges.append(f"{start}-{end}")
    time_str = ", ".join(ranges)

    return f"💤 {total_duration//60}h {total_duration%60}m  {time_str}"


def get_nap_str(conn, today):
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT start_time, duration_minutes FROM nap_logs WHERE jalali_date=? ORDER BY start_time",
        (today,),
    ).fetchall()
    if not rows:
        return ""

    total = sum(r["duration_minutes"] for r in rows if r["duration_minutes"])
    ranges = []
    for r in rows:
        start = datetime.fromtimestamp(r["start_time"]).strftime("%H:%M")
        end = datetime.fromtimestamp(r["start_time"] + r["duration_minutes"] * 60).strftime("%H:%M")
        ranges.append(f"{start}-{end}")
    time_str = ", ".join(ranges)

    return f"😴 {total//60}h {total%60}m  {time_str}"
