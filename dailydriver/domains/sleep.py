# dailydriver/domains/sleep.py
import time
from datetime import datetime
from dailydriver.core.database import get_connection_cm
from dailydriver.utils.time_utils import today_jalali
from dailydriver.utils.time_parser import parse_time_range
from dailydriver.ui.terminal_ui import current_ui

def log_sleep(cmd: str):
    parts = cmd.strip().split()
    if len(parts) < 2:
        current_ui.print_line("Usage: S <sleep> <wake>   or   S <sleep>-<wake>")
        return None

    now = datetime.now()
    sleep_dt, wake_dt, duration = parse_time_range(parts[1:], now)
    if sleep_dt is None:
        current_ui.print_line("Could not parse sleep/wake times.")
        return None

    assert sleep_dt is not None
    assert wake_dt is not None
    assert duration is not None

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
