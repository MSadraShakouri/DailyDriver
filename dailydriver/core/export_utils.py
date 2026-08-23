"""Shared helpers for timeline-style exports."""

from __future__ import annotations

import jdatetime


def parse_duration_arg(arg: str) -> int | None:
    """Parse ``7d``, ``2w``, ``3m``, ``1y``, a bare day count, or ``all``."""
    arg = arg.strip().lower()
    if not arg:
        return None
    if arg == "all":
        return 0
    if arg.endswith("d"):
        number = arg[:-1]
        return int(number) if number.isdigit() else None
    if arg.endswith("w"):
        number = arg[:-1]
        return int(number) * 7 if number.isdigit() else None
    if arg.endswith("m"):
        number = arg[:-1]
        return int(number) * 30 if number.isdigit() else None
    if arg.endswith("y"):
        number = arg[:-1]
        return int(number) * 365 if number.isdigit() else None
    if arg.isdigit():
        return int(arg)
    return None


def jalali_date_time(ts: int | float) -> tuple[str, str]:
    """Return ``(DD Month YYYY, HH:MM)`` for a local Unix timestamp."""
    dt = jdatetime.datetime.fromtimestamp(ts)
    return dt.strftime("%d %B %Y"), dt.strftime("%H:%M")


def format_duration_minutes(minutes: int | None) -> str:
    """Return a compact human-readable duration."""
    if minutes is None:
        return ""
    hours, mins = divmod(int(minutes), 60)
    if hours and mins:
        return f"{hours}h {mins}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


def format_time_range(start_ts: int, duration_minutes: int | None) -> str:
    """Return ``HH:MM`` or ``HH:MM → HH:MM (dur)`` from a start timestamp."""
    _, start_time = jalali_date_time(start_ts)
    if duration_minutes is None:
        return start_time
    finish_ts = start_ts + int(duration_minutes) * 60
    _, finish_time = jalali_date_time(finish_ts)
    duration = format_duration_minutes(duration_minutes)
    return f"{start_time} → {finish_time} ({duration})" if duration else f"{start_time} → {finish_time}"


def build_export_item(
    timestamp: int,
    text: str,
    display_time: str | None = None,
    *,
    details: str | None = None,
    sort_key=None,
) -> dict:
    """Create a normalized unified timeline item."""
    display_date, inferred_time = jalali_date_time(timestamp)
    return {
        "timestamp": int(timestamp),
        "display_date": display_date,
        "display_time": display_time or inferred_time,
        "text": text,
        "details": details or "",
        "sort_key": sort_key if sort_key is not None else (int(timestamp), text),
    }
