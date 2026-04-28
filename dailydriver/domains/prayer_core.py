# dailydriver/domains/prayer_core.py
from datetime import datetime

# Fixed prayer times (24h)
PRAYER_TIMES = {
    'fajr': 4.5,          # 4:30
    'dhuhr_asr': 13.0,    # 13:00
    'maghrib_isha': 19.5, # 19:30
}

PRAYER_SLOTS = ['fajr', 'dhuhr_asr', 'maghrib_isha']

def current_slot() -> str:
    """Guess which prayer slot is most recent based on current time."""
    now = datetime.now().hour + datetime.now().minute / 60.0
    if now < PRAYER_TIMES['dhuhr_asr'] - 1:
        return 'fajr'
    elif now < PRAYER_TIMES['maghrib_isha'] - 1:
        return 'dhuhr_asr'
    else:
        return 'maghrib_isha'
