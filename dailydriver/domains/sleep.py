import time
from datetime import datetime, timedelta
from dailydriver.core.database import get_connection_cm
from dailydriver.utils.time_utils import today_jalali
from dailydriver.ui.terminal_ui import current_ui

def log_sleep(cmd: str):
    parts = cmd.strip().split()
    if len(parts) < 2:
        current_ui.print_line("Usage: S <sleep> <wake>   or   S <sleep>-<wake>")
        return None

    if len(parts) == 2 and '-' in parts[1]:
        compact_parts = parts[1].split('-')
        if len(compact_parts) != 2:
            current_ui.print_line("Invalid format. Use S <sleep>-<wake> (e.g., S 2-8:30)")
            return None
        sleep_str, wake_str = compact_parts[0], compact_parts[1]
    elif len(parts) >= 3:
        sleep_str = parts[1]
        wake_str = parts[2]
    else:
        current_ui.print_line("Usage: S <sleep> <wake>   or   S <sleep>-<wake>")
        return None

    now = datetime.now()
    sleep_dt = parse_time(sleep_str, now, is_sleep=True)
    if sleep_dt is None:
        current_ui.print_line("Could not parse sleep time.")
        return None
    wake_dt = parse_time(wake_str, now, is_sleep=False)
    if wake_dt is None:
        current_ui.print_line("Could not parse wake time.")
        return None

    if wake_dt <= sleep_dt:
        wake_dt += timedelta(days=1)

    duration = int((wake_dt - sleep_dt).total_seconds() / 60)

    if not current_ui.confirm(
        f"Sleep:  {sleep_dt.strftime('%H:%M')}\n"
        f"Wake:   {wake_dt.strftime('%H:%M')}\n"
        f"Duration: {duration//60}h {duration%60}m"
    ):
        return None

    with get_connection_cm() as conn:
        cur = conn.cursor()
        today = today_jalali()
        cur.execute(
            "INSERT INTO sleep_logs (jalali_date, sleep_time, wake_time, duration_minutes) VALUES (?,?,?,?)",
            (today, int(sleep_dt.timestamp()), int(wake_dt.timestamp()), duration)
        )
        conn.commit()

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
