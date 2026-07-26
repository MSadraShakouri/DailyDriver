"""Day start hour handling – shifts what 'today' means for hygiene and targets."""

from datetime import datetime, timedelta

import jdatetime

from dailydriver.core.database import get_connection_cm


def get_day_start_hour() -> int:
    """Return the hour (0-23) at which a new day begins. Default 4 (4:00 AM)."""
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute("SELECT value FROM meta WHERE key = 'day_start_hour'")
        row = cur.fetchone()
        if row:
            try:
                return int(row["value"])
            except (ValueError, TypeError):
                return 4
        return 4


def set_day_start_hour(hour: int) -> None:
    """Set the day start hour (0-23)."""
    if not (0 <= hour <= 23):
        raise ValueError(f"Hour must be between 0 and 23, got {hour}")
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('day_start_hour', ?)",
            (str(hour),)
        )
        conn.commit()


def get_shifted_today(now: datetime | None = None) -> jdatetime.date:
    if now is None:
        now = datetime.now()
    hour = get_day_start_hour()
    # Convert now to Jalali date
    jdate = jdatetime.date.fromgregorian(date=now.date())
    if now.hour < hour:
        return jdate - timedelta(days=1)
    return jdate
