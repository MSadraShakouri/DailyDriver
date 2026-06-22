# dailydriver/utils/intervals.py
"""Shared interval scheduling logic for qada and nazr features.

Interval types and their value encoding (TEXT column):
  n_days   : "3"          (integer as string; NULL or "0" → returns None)
  daily    : NULL or ""   (value is ignored)
  weekly   : "2"          (0=Saturday in Jalali week; Monday=2)
  monthly  : "1,15"       (comma‑separated day numbers)
"""

from datetime import datetime, timedelta

import jdatetime


def next_instance_date(
    interval_type: str,
    interval_value: str | None,
    calendar: str,
    last_fulfilled_date: jdatetime.date | None,
    reference_date: jdatetime.date,
) -> jdatetime.date | None:
    """Compute the next scheduled instance date.

    If *last_fulfilled_date* is None, the first instance is the next
    scheduled date that is >= *reference_date*.  If *reference_date*
    itself is a scheduled date, the first instance is that date.
    """
    # --- helper: compute next from a given base date (exclusive for n_days, inclusive for others) ---
    itype = interval_type.strip().lower()
    ival = (interval_value or "").strip()

    if itype == "n_days":
        if not ival or not ival.isdigit():
            return None
        n = int(ival)
        if n < 1:
            return None
        if last_fulfilled_date is not None:
            return last_fulfilled_date + jdatetime.timedelta(days=n)
        else:
            return reference_date  # first instance is the reference date itself

    # For daily/weekly/monthly, we'll scan from the appropriate starting point
    if last_fulfilled_date is not None:
        start = last_fulfilled_date
    else:
        start = reference_date

    if itype == "daily":
        if last_fulfilled_date is not None:
            return start + jdatetime.timedelta(days=1)
        else:
            return start  # first instance is the reference date itself

    elif itype == "weekly":
        if not ival or not ival.isdigit():
            return None
        target_wd = int(ival) % 7
        current_wd = start.weekday()  # 0=Sat
        if last_fulfilled_date is not None:
            # start is the fulfilled date; we need to move past it
            days_ahead = (target_wd - current_wd) % 7
            if days_ahead == 0:
                days_ahead = 7
            return start + jdatetime.timedelta(days=days_ahead)
        else:
            # first instance: start is reference_date; can be the same day
            days_ahead = (target_wd - current_wd) % 7
            # if days_ahead == 0 and reference_date is the target weekday, that's the first instance
            return start + jdatetime.timedelta(days=days_ahead)

    elif itype == "monthly":
        if not ival:
            return None
        try:
            days = [int(d.strip()) for d in ival.split(",") if d.strip().isdigit()]
        except ValueError:
            return None
        if not days:
            return None
        # scan forward from start (inclusive if first instance, exclusive if subsequent)
        check = start if last_fulfilled_date is None else (start + jdatetime.timedelta(days=1))
        for _ in range(366):
            if check.day in days:
                try:
                    jdatetime.date(check.year, check.month, check.day)
                    return check
                except ValueError:
                    pass
            check += jdatetime.timedelta(days=1)
        return None

    return None


def is_instance_active(instance_date: jdatetime.date, now: datetime) -> bool:
    """Return True if *instance_date* is today (the day of *now*)."""
    today = jdatetime.date.today()
    return instance_date == today


def window_ends_at(interval_type: str, instance_date: jdatetime.date) -> datetime | None:
    """Return the datetime when the window for *instance_date* closes.

    For daily/weekly/monthly: 23:59:59 on *instance_date* (local time).
    For n_days: returns None (instances never expire).
    """
    itype = interval_type.strip().lower()
    if itype == "n_days":
        return None
    # Convert Jalali date to Gregorian to build a datetime
    gdate = instance_date.togregorian()
    return datetime(gdate.year, gdate.month, gdate.day, 23, 59, 59)
