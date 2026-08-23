"""Prayer status for the daily header."""

from datetime import datetime


def get_prayer_parts(conn, today):
    cur = conn.cursor()
    slot_info = [
        ("fajr", "🌅", "F"),
        ("dhuhr_asr", "☀️", "DA"),
        ("maghrib_isha", "🌆", "MI"),
    ]
    parts = []
    for slot, emoji, _ in slot_info:
        row = cur.execute(
            "SELECT prayer_time FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
            (slot, today),
        ).fetchone()
        if row and row["prayer_time"]:
            dt = datetime.fromtimestamp(row["prayer_time"])
            time_str = dt.strftime("%H:%M")
            parts.append(f"{emoji} {time_str}")
        else:
            parts.append(f"{emoji}  — ")
    return parts
