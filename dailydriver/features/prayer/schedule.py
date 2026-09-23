from datetime import datetime

from dailydriver.features.prayer.windows import get_slot_windows

PRAYER_SLOTS = ["fajr", "dhuhr_asr", "maghrib_isha"]
SLOT_LABELS = {
    "fajr": "Fajr",
    "dhuhr_asr": "Dhuhr & Asr",
    "maghrib_isha": "Maghrib & Isha",
}


def current_slot(now=None) -> str:
    """Guess which prayer slot is most recent based on today's window opens."""
    if now is None:
        now = datetime.now()
    windows = get_slot_windows(now.date())

    current = "fajr"
    for slot in PRAYER_SLOTS:
        if now >= windows[slot].opens:
            current = slot
        else:
            break
    return current
