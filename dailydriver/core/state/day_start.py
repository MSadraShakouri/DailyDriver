"""Day-boundary preferences and helpers."""

from __future__ import annotations

from datetime import datetime, timedelta

import jdatetime

from .meta import get_meta_value, set_meta_value

_DAY_START_KEY = "day_start_hour"
_DEFAULT_DAY_START_HOUR = 4


def get_day_start_hour() -> int:
    """Return the configured day-boundary hour, defaulting to 4."""
    value = get_meta_value(_DAY_START_KEY)
    if value is None:
        return _DEFAULT_DAY_START_HOUR
    try:
        return int(value)
    except (ValueError, TypeError):
        return _DEFAULT_DAY_START_HOUR


def set_day_start_hour(hour: int) -> None:
    """Persist the hour at which a new day begins."""
    if not (0 <= hour <= 23):
        raise ValueError(f"Hour must be between 0 and 23, got {hour}")
    set_meta_value(_DAY_START_KEY, str(hour))


def get_shifted_today(now: datetime | None = None) -> jdatetime.date:
    if now is None:
        now = datetime.now()
    jdate = jdatetime.date.fromgregorian(date=now.date())
    if now.hour < get_day_start_hour():
        return jdate - timedelta(days=1)
    return jdate


def shift_timestamp_to_date(timestamp: int | float) -> jdatetime.date:
    dt = datetime.fromtimestamp(timestamp)
    jdate = jdatetime.date.fromgregorian(date=dt.date())
    if dt.hour < get_day_start_hour():
        return jdate - timedelta(days=1)
    return jdate
