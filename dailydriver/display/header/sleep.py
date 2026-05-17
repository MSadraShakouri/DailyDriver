# dailydriver/display/header/sleep.py
"""Sleep and nap header lines."""
from datetime import datetime

def get_sleep_str(conn, today):
    cur = conn.cursor()
    row = cur.execute(
        "SELECT sleep_time, wake_time, duration_minutes FROM sleep_logs WHERE jalali_date=?",
        (today,)
    ).fetchone()
    if row:
        start_dt = datetime.fromtimestamp(row['sleep_time'])
        end_dt = datetime.fromtimestamp(row['wake_time'])
        d = row['duration_minutes']
        return f"💤 {d//60}h {d%60}m  {start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')}"
    return "💤 —"

def get_nap_str(conn, today):
    cur = conn.cursor()
    row = cur.execute(
        "SELECT SUM(duration_minutes) FROM nap_logs WHERE jalali_date=?",
        (today,)
    ).fetchone()
    total = row[0] if row and row[0] is not None else 0
    if total:
        return f"😴 {total//60}h {total%60}m"
    return ""
