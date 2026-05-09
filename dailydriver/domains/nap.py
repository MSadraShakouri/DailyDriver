# dailydriver/domains/nap.py
import time
from datetime import datetime
from dailydriver.core.database import get_connection_cm
from dailydriver.utils.time_utils import today_jalali
from dailydriver.utils.time_parser import parse_time_range
from dailydriver.ui.terminal_ui import current_ui

def log_nap(cmd: str):
    parts = cmd.strip().split()
    args = parts[1:] if len(parts) > 1 else []

    if not args:
        current_ui.print_line("Usage: nap <start> <end>   or   nap <start>-<end>")
        return None

    now = datetime.now()
    start_dt, end_dt, duration = parse_time_range(args, now)

    if start_dt is None:
        current_ui.print_line("Could not parse start/end times.")
        return None

    if duration is not None and duration < 1:
        current_ui.print_line("Duration must be positive.")
        return None

    if not current_ui.confirm(
        f"Nap:   {start_dt.strftime('%H:%M')} → {end_dt.strftime('%H:%M')}\n"
        f"Duration: {duration//60}h {duration%60}m"
    ):
        return None

    with get_connection_cm() as conn:
        cur = conn.cursor()
        today = today_jalali()
        cur.execute(
            "INSERT INTO nap_logs (jalali_date, start_time, duration_minutes, description) VALUES (?,?,?,?)",
            (today, int(start_dt.timestamp()), duration, None)
        )
        conn.commit()

    return f"Nap logged: {start_dt.strftime('%H:%M')} → {end_dt.strftime('%H:%M')} ({duration//60}h {duration%60}m)"
