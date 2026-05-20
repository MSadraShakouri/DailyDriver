# dailydriver/domains/sleep.py
from datetime import datetime
from dailydriver.core.database import get_connection_cm
from dailydriver.core.logger import get_last_action_time
from dailydriver.utils.time_utils import today_jalali
from dailydriver.utils.time_parser import parse_time_expressions
from dailydriver.ui.terminal_ui import current_ui

def log_sleep(cmd: str):
    parts = cmd.strip().split()
    if len(parts) < 2:
        current_ui.print_line("Usage: S <sleep> <wake>   or   S <sleep>-<wake>")
        return None

    now = datetime.now()
    last_ts = get_last_action_time()
    last_time = datetime.fromtimestamp(last_ts) if last_ts else None

    # Build a single time‑expression string.
    # Old syntax "S 23:00 07:15" → two tokens, no dash → join with "-".
    args = parts[1:]
    if len(args) == 2 and '-' not in args[0] and '-' not in args[1]:
        time_str = f"{args[0]}-{args[1]}"
    else:
        time_str = " ".join(args)

    interpretations = parse_time_expressions(
        time_str, now, last_time=last_time, mode="required"
    )

    # Keep only interpretations that have an end time (required for sleep)
    valid = [i for i in interpretations if i.end is not None]

    if not valid:
        current_ui.print_line(
            "Duration required. Use a range (e.g., 23:00-7:00, l-9, 23-n, l--10)."
        )
        return None

    selected = valid[0]
    sleep_dt = selected.start
    wake_dt = selected.end
    duration = selected.duration_minutes

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
