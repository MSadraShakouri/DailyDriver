# dailydriver/domains/prayer_core.py
from datetime import datetime

import jdatetime

from dailydriver.utils.prayer_times import get_approximate_times

PRAYER_SLOTS = ["fajr", "dhuhr_asr", "maghrib_isha"]


def _today_times():
    """Return today's prayer times as datetime objects."""
    today_j = jdatetime.date.today()
    times = get_approximate_times(today_j.month, today_j.day)
    now = datetime.now()

    def to_dt(hour_min):
        h, m = hour_min
        return now.replace(hour=h, minute=m, second=0, microsecond=0)

    return {
        "fajr": to_dt(times["fajr"]),
        "dhuhr": to_dt(times["dhuhr"]),
        "maghrib": to_dt(times["maghrib"]),
    }


def current_slot() -> str:
    """Guess which prayer slot is most recent based on today's times."""
    times = _today_times()
    now = datetime.now()

    ordered = [
        ("fajr", times["fajr"]),
        ("dhuhr_asr", times["dhuhr"]),
        ("maghrib_isha", times["maghrib"]),
    ]

    current = "fajr"
    for slot, dt in ordered:
        if now >= dt:
            current = slot
        else:
            break
    return current
