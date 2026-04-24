import time
from datetime import datetime
from database import get_connection
from utils import today_jalali

# Fixed prayer times (24h) – you can adjust later
PRAYER_TIMES = {
    'fajr': 4.5,          # 4:30
    'dhuhr_asr': 13.0,    # 13:00
    'maghrib_isha': 19.5, # 19:30
}

PRAYER_SLOTS = ['fajr', 'dhuhr_asr', 'maghrib_isha']

def current_slot() -> str:
    """Guess which prayer slot is most recent based on current time."""
    now = datetime.now().hour + datetime.now().minute / 60.0
    if now < PRAYER_TIMES['dhuhr_asr'] - 1:  # before ~12:00
        return 'fajr'
    elif now < PRAYER_TIMES['maghrib_isha'] - 1:
        return 'dhuhr_asr'
    else:
        return 'maghrib_isha'

def log_prayer(cmd: str):
    """
    Parse a 'P' command, ask for slot if needed, and log.
    """
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()

    # Strip 'p' and optional offset/time
    parts = cmd.strip().split()
    offset_min = 0
    explicit_time = None
    if len(parts) > 1:
        arg = parts[1]
        if arg.startswith('-'):
            try:
                offset_min = int(arg[1:])
            except ValueError:
                print("Invalid offset.")
                conn.close()
                return
        else:
            # Try to parse as time like 4:30 or 14:00
            try:
                t = datetime.strptime(arg, '%H:%M')
                explicit_time = t.hour * 60 + t.minute
            except ValueError:
                print("Time not understood. Use HH:MM or -15 offset.")
                conn.close()
                return

    # Determine slot
    if explicit_time:
        # crude guess: <10 -> fajr, <17 -> dhuhr_asr, else maghrib_isha
        hour = explicit_time / 60
        if hour < 10:
            slot = 'fajr'
        elif hour < 17:
            slot = 'dhuhr_asr'
        else:
            slot = 'maghrib_isha'
    else:
        slot = current_slot()
        if offset_min:
            # adjust? just logging offset from current slot time.
            pass

    # Confirm with user
    print(f"Slot: {slot}")
    confirm = input("Log as on_time? (y/n): ").strip().lower()
    if confirm != 'y':
        conn.close()
        return

    # Determine prayer time (approx)
    base_time = PRAYER_TIMES.get(slot, 0)
    prayer_dt = datetime.now().replace(hour=int(base_time), minute=int((base_time % 1) * 60), second=0, microsecond=0)
    if offset_min:
        prayer_dt = prayer_dt - time_offset(offset_min)
    if explicit_time:
        prayer_dt = datetime.now().replace(hour=explicit_time//60, minute=explicit_time%60, second=0, microsecond=0)

    # Insert into prayer_logs
    cur.execute(
        "INSERT OR REPLACE INTO prayer_logs (prayer_slot, jalali_date, status, logged_at) VALUES (?,?,?,?)",
        (slot, today, 'on_time', int(time.time()))
    )
    conn.commit()
    print(f"Logged {slot} on_time.")
    conn.close()

def time_offset(minutes):
    from datetime import timedelta
    return timedelta(minutes=minutes)
