"""Prayer status for the daily header."""

from datetime import datetime

from .store import get_prayer_log


def get_prayer_parts(conn, today):
    slot_info = [
        ("fajr", "🌅", "F"),
        ("dhuhr_asr", "☀️", "DA"),
        ("maghrib_isha", "🌆", "MI"),
    ]
    parts = []
    for slot, emoji, _ in slot_info:
        row = get_prayer_log(conn, slot, today)
        if row and row["prayer_time"]:
            dt = datetime.fromtimestamp(row["prayer_time"])
            time_str = dt.strftime("%H:%M")
            parts.append(f"{emoji} {time_str}")
        else:
            parts.append(f"{emoji}  — ")
    return parts
