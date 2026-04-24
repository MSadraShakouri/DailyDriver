import time
from datetime import datetime, timedelta
from database import get_connection
from utils import today_jalali

def log_sleep(cmd: str):
    """
    Parse 'S <sleep_time> <wake_time>'
    sleep_time: HH:MM, or integer hour, or 'n' (now)
    wake_time: HH:MM, or 'n' (now), or '-30' (minutes ago), or integer hour
    """
    parts = cmd.strip().split()
    if len(parts) < 3:
        print("Usage: S <sleep_time> <wake_time>  e.g., S 2 8:30")
        return

    sleep_str = parts[1]
    wake_str = parts[2]

    now = datetime.now()

    # Parse sleep time
    sleep_dt = parse_time(sleep_str, now, is_sleep=True)
    if sleep_dt is None:
        print("Could not parse sleep time.")
        return

    # Parse wake time
    wake_dt = parse_time(wake_str, now, is_sleep=False)
    if wake_dt is None:
        print("Could not parse wake time.")
        return

    # If wake is before sleep, assume next day
    if wake_dt <= sleep_dt:
        wake_dt += timedelta(days=1)

    duration = int((wake_dt - sleep_dt).total_seconds() / 60)

    # Save to sleep_logs (and maybe an entry)
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()
    cur.execute(
        "INSERT INTO sleep_logs (jalali_date, sleep_time, wake_time, duration_minutes) VALUES (?,?,?,?)",
        (today, int(sleep_dt.timestamp()), int(wake_dt.timestamp()), duration)
    )
    conn.commit()
    print(f"Sleep logged: {sleep_dt.strftime('%H:%M')} → {wake_dt.strftime('%H:%M')} ({duration//60}h {duration%60}m)")
    conn.close()

def parse_time(s: str, now: datetime, is_sleep: bool):
    """Parse a time string into a datetime object."""
    s = s.strip().lower()
    if s == 'n':
        return now
    if s.startswith('-'):
        try:
            mins = int(s[1:])
            return now - timedelta(minutes=mins)
        except ValueError:
            return None
    # Try HH:MM
    try:
        t = datetime.strptime(s, '%H:%M').time()
        return now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
    except ValueError:
        pass
    # Try integer hour
    try:
        hour = int(s)
        return now.replace(hour=hour, minute=0, second=0, microsecond=0)
    except ValueError:
        pass
    return None
