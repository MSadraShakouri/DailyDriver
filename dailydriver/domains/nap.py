# dailydriver/domains/nap.py
import time
from datetime import datetime, timedelta
from dailydriver.core.database import get_connection_cm
from dailydriver.utils.time_utils import today_jalali
from dailydriver.utils.time_parser import parse_duration, parse_time, parse_time_range
from dailydriver.ui.terminal_ui import current_ui

def log_nap(cmd: str):
    parts = cmd.strip().split()
    args = parts[1:] if len(parts) > 1 else []
    start_time = None
    duration = None

    now = datetime.now()

    if not args:
        # interactive
        start_str = current_ui.prompt("Start time (HH:MM or Enter=now): ").strip()
        if not start_str:
            start_time = int(time.time())
        else:
            start_dt = parse_time(start_str, now)
            if start_dt is None:
                current_ui.print_line("Invalid time format (use HH:MM, n, -30, etc.).")
                return None
            start_time = int(start_dt.timestamp())

        dur_str = current_ui.prompt("Duration (e.g. 30m, 1h, 14:25 for end time): ").strip()
        if not dur_str:
            current_ui.print_line("Duration required.")
            return None
        # try as end time first
        end_dt = parse_time(dur_str, now, allow_future=True)
        if end_dt:
            duration = int((end_dt - datetime.fromtimestamp(start_time)).total_seconds() / 60)
            if duration <= 0:
                duration += 24 * 60
        else:
            duration = parse_duration(dur_str)
            if duration is None:
                current_ui.print_line("Invalid duration (use 30m, 1h, 1h15m, or HH:MM).")
                return None
    elif len(args) == 1:
        # duration or start time
        dur = parse_duration(args[0])
        if dur is not None:
            duration = dur
            start_time = int(time.time() - duration * 60)
        else:
            start_dt = parse_time(args[0], now)
            if start_dt is None:
                current_ui.print_line("Invalid argument. Use 30m, 1h, 14:00, or 14:00 14:25.")
                return None
            start_time = int(start_dt.timestamp())
            dur_str = current_ui.prompt("Duration (e.g. 30m, 1h, or HH:MM end time): ").strip()
            if not dur_str:
                current_ui.print_line("Duration required.")
                return None
            end_dt = parse_time(dur_str, now, allow_future=True)
            if end_dt:
                duration = int((end_dt - datetime.fromtimestamp(start_time)).total_seconds() / 60)
                if duration <= 0:
                    duration += 24 * 60
            else:
                duration = parse_duration(dur_str)
                if duration is None:
                    current_ui.print_line("Invalid duration.")
                    return None
    elif len(args) == 2:
        # start and end, or start and duration
        start_dt, end_dt, dur = parse_time_range(args, now)
        if start_dt is not None:
            start_time = int(start_dt.timestamp())
            duration = dur
        else:
            # fall back to start + duration string
            start_dt = parse_time(args[0], now)
            if start_dt is None:
                current_ui.print_line("Invalid start time.")
                return None
            start_time = int(start_dt.timestamp())
            dur = parse_duration(args[1])
            if dur is None:
                current_ui.print_line("Invalid second argument (use HH:MM or duration).")
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
