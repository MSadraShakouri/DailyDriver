# dailydriver/domains/nap.py
import time, re
from datetime import datetime, timedelta
from dailydriver.core.database import get_connection_cm
from dailydriver.utils.time_utils import today_jalali
from dailydriver.ui.terminal_ui import current_ui

def _parse_duration(s):
    """Parse a duration string like '30m', '1h', '1h15m'. Return minutes or None."""
    s = s.strip().lower()
    # "30m" or "30 min"
    m = re.match(r'^(\d+)\s*min(?:ute)?s?$', s)
    if m:
        return int(m.group(1))
    m = re.match(r'^(\d+)\s*m$', s)
    if m:
        return int(m.group(1))
    # "1h"
    m = re.match(r'^(\d+)\s*h(?:ou)?r?s?$', s)
    if m:
        return int(m.group(1)) * 60
    # "1h15m" or "1h15"
    m = re.match(r'^(\d+)\s*h\s*(?:(\d+)\s*m?)?$', s)
    if m:
        hours = int(m.group(1))
        mins = int(m.group(2)) if m.group(2) else 0
        return hours * 60 + mins
    return None

def _parse_time(s, now):
    """Parse a HH:MM time string and return a datetime on the current day (or yesterday if in the future)."""
    try:
        t = datetime.strptime(s.strip(), '%H:%M')
        dt = now.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)
        if dt > now:
            dt -= timedelta(days=1)
        return dt
    except ValueError:
        return None

def log_nap(cmd: str):
    """
    Log a nap.
      nap               – interactive
      nap 30m           – nap of 30 min starting 30 min ago
      nap 14:00 14:25   – nap from 14:00 to 14:25
      nap 14:00 30m     – nap starting at 14:00, duration 30 min
    """
    parts = cmd.strip().split()
    args = parts[1:] if len(parts) > 1 else []
    start_time = None
    duration = None

    now = datetime.now()

    if not args:
        # --- interactive ---
        start_str = current_ui.prompt("Start time (HH:MM or Enter=now): ").strip()
        if not start_str:
            start_time = int(time.time())
        else:
            start_dt = _parse_time(start_str, now)
            if start_dt is None:
                current_ui.print_line("Invalid time format (use HH:MM).")
                return None
            start_time = int(start_dt.timestamp())

        dur_str = current_ui.prompt("Duration (e.g. 30m, 1h, 14:25 for end time): ").strip()
        if not dur_str:
            current_ui.print_line("Duration required.")
            return None
        # try as end time first
        end_dt = _parse_time(dur_str, now)
        if end_dt:
            # end time given
            duration = int((end_dt - datetime.fromtimestamp(start_time)).total_seconds() / 60)
            if duration <= 0:
                duration += 24 * 60   # next day
        else:
            # try as duration string
            duration = _parse_duration(dur_str)
            if duration is None:
                current_ui.print_line("Invalid duration (use 30m, 1h, 1h15m, or HH:MM).")
                return None
    else:
        # --- parse args ---
        if len(args) == 1:
            # either duration like "30m" or start time "14:00"
            dur = _parse_duration(args[0])
            if dur is not None:
                duration = dur
                start_time = int(time.time() - duration * 60)
            else:
                # maybe a start time?
                start_dt = _parse_time(args[0], now)
                if start_dt is None:
                    current_ui.print_line("Invalid argument. Use 30m, 1h, 14:00, or 14:00 14:25.")
                    return None
                start_time = int(start_dt.timestamp())
                # prompt for duration if not given
                dur_str = current_ui.prompt("Duration (e.g. 30m, 1h, or HH:MM end time): ").strip()
                if not dur_str:
                    current_ui.print_line("Duration required.")
                    return None
                end_dt = _parse_time(dur_str, now)
                if end_dt:
                    duration = int((end_dt - datetime.fromtimestamp(start_time)).total_seconds() / 60)
                    if duration <= 0:
                        duration += 24 * 60
                else:
                    duration = _parse_duration(dur_str)
                    if duration is None:
                        current_ui.print_line("Invalid duration.")
                        return None
        elif len(args) == 2:
            # start and end time (HH:MM HH:MM) or start and duration (14:00 30m)
            start_dt = _parse_time(args[0], now)
            if start_dt is None:
                current_ui.print_line("Invalid start time.")
                return None
            start_time = int(start_dt.timestamp())
            # second arg: end time or duration?
            end_dt = _parse_time(args[1], now)
            if end_dt:
                duration = int((end_dt - start_dt).total_seconds() / 60)
                if duration <= 0:
                    duration += 24 * 60
            else:
                dur = _parse_duration(args[1])
                if dur is None:
                    current_ui.print_line("Invalid second argument (use HH:MM or 30m, etc.).")
                    return None
                duration = dur
        else:
            current_ui.print_line("Usage: nap [30m|1h|14:00|14:00 14:25|14:00 30m]")
            return None

    if start_time is None or duration is None:
        return None

    with get_connection_cm() as conn:
        cur = conn.cursor()
        today = today_jalali()
        cur.execute(
            "INSERT INTO nap_logs (jalali_date, start_time, duration_minutes, description) VALUES (?,?,?,?)",
            (today, start_time, duration, None)
        )
        conn.commit()

    start_dt = datetime.fromtimestamp(start_time)
    return f"Nap logged: {start_dt.strftime('%H:%M')} → {duration} min"