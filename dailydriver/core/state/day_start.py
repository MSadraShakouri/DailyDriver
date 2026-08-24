"""Day-boundary preferences and helpers."""

from __future__ import annotations

from datetime import datetime, timedelta

import jdatetime

from .meta import get_meta_value, set_meta_value

_DAY_START_KEY = "day_start_hour"
_DEFAULT_DAY_START_HOUR = 4

_DAY_VIEW_MODE_KEY = "day_view_mode"
DAY_VIEW_MODE_MIDNIGHT = "midnight"
DAY_VIEW_MODE_DAY_START = "daystart"
_VALID_DAY_VIEW_MODES = (DAY_VIEW_MODE_MIDNIGHT, DAY_VIEW_MODE_DAY_START)


def get_day_view_mode() -> str:
    """Return the persisted day-view boundary mode, defaulting to midnight."""
    value = get_meta_value(_DAY_VIEW_MODE_KEY)
    if value in _VALID_DAY_VIEW_MODES:
        return value
    return DAY_VIEW_MODE_MIDNIGHT


def set_day_view_mode(mode: str) -> None:
    """Persist the day-view boundary mode ('midnight' or 'daystart')."""
    if mode not in _VALID_DAY_VIEW_MODES:
        raise ValueError(f"Mode must be one of {_VALID_DAY_VIEW_MODES}, got {mode!r}")
    set_meta_value(_DAY_VIEW_MODE_KEY, mode)


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
