import time
from datetime import datetime, timedelta
from database import get_connection
from database import commit_and_update
from utils import today_jalali

def log_sleep(cmd: str):
    """
    Parse 'S' command:
      S <sleep_time> <wake_time>        e.g., S 2 8:30
      S <sleep_time>-<wake_time>        e.g., S 2-8:30
    Returns a result string (or None if cancelled/error).
    """
    parts = cmd.strip().split()
    if len(parts) < 2:
        print("Usage: S <sleep> <wake>   or   S <sleep>-<wake>")
        return None

    # Check for compact form: second token contains '-'
    if len(parts) == 2 and '-' in parts[1]:
        compact_parts = parts[1].split('-')
        if len(compact_parts) != 2:
            print("Invalid format. Use S <sleep>-<wake> (e.g., S 2-8:30)")
            return None
        sleep_str, wake_str = compact_parts[0], compact_parts[1]
    elif len(parts) >= 3:
        sleep_str = parts[1]
        wake_str = parts[2]
    else:
        print("Usage: S <sleep> <wake>   or   S <sleep>-<wake>")
        return None

    now = datetime.now()

    sleep_dt = parse_time(sleep_str, now, is_sleep=True)
    if sleep_dt is None:
        print("Could not parse sleep time.")
        return None

    wake_dt = parse_time(wake_str, now, is_sleep=False)
    if wake_dt is None:
        print("Could not parse wake time.")
        return None

    if wake_dt <= sleep_dt:
        wake_dt += timedelta(days=1)

    duration = int((wake_dt - sleep_dt).total_seconds() / 60)

    # Confirm
    print(f"\nSleep:  {sleep_dt.strftime('%H:%M')}")
    print(f"Wake:   {wake_dt.strftime('%H:%M')}")
    print(f"Duration: {duration//60}h {duration%60}m")
    print("(Enter=yes, n=cancel)")
    confirm = input("> ").strip().lower()
    if confirm == 'n':
        return None

    # Save
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()
    cur.execute(
        "INSERT INTO sleep_logs (jalali_date, sleep_time, wake_time, duration_minutes) VALUES (?,?,?,?)",
        (today, int(sleep_dt.timestamp()), int(wake_dt.timestamp()), duration)
    )
    commit_and_update(conn)
    conn.close()

    # Build result
    result = "Sleep logged:\n"
    result += f"  {sleep_dt.strftime('%H:%M')} → {wake_dt.strftime('%H:%M')}\n"
    result += f"  {duration//60}h {duration%60}m"
    return result

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
