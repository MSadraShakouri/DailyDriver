import time
import jdatetime
from datetime import datetime
from ui import current_ui

def days_ago(n: int) -> int:
    """Return Unix timestamp for exactly n days ago (now - n*86400)."""
    return int(time.time()) - n * 86400

def today_start_ts() -> int:
    """Return Unix timestamp for the start of today (00:00:00)."""
    return int(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp())


def today_jalali() -> str:
    """Return today's Jalali date as 'YYYY-MM-DD'."""
    return jdatetime.date.today().strftime('%Y-%m-%d')

def format_jalali(date_str: str) -> str:
    """Convert 'YYYY-MM-DD' to 'D Month Year'."""
    y, m, d = map(int, date_str.split('-'))
    return jdatetime.date(y, m, d).strftime('%d %B %Y')
