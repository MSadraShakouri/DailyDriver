"""Small presentation helpers shared by interactive feature managers."""

from __future__ import annotations

import jdatetime

WEEKDAYS = ("Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday")


def format_percentage(value: float) -> str:
    """Format a percentage with at most two decimal places."""
    if value == 0:
        return "0%"
    return f"{value:.2f}".rstrip("0").rstrip(".") + "%"


def format_due_date(due: jdatetime.date | None, today: jdatetime.date) -> str:
    """Describe a due date relative to *today*."""
    if due is None:
        return "-"
    days = (due - today).days
    if days < 0:
        return "Overdue"
    if days == 0:
        return "today"
    if days == 1:
        return "tomorrow"
    return f"in {days} days"


def format_interval(entry: dict) -> str:
    """Return a human-readable recurrence from an entry-like dictionary."""
    interval_type = entry.get("interval_type") or "daily"
    value = entry.get("interval_value")
    if interval_type == "daily":
        return "daily"
    if interval_type == "n_days":
        return f"every {value} days"
    if interval_type == "weekly":
        try:
            return f"weekly on {WEEKDAYS[int(value)]}"
        except (ValueError, TypeError, IndexError):
            return f"weekly on {value}"
    if interval_type == "monthly":
        return f"monthly on {value}"
    return interval_type


def parse_jalali_date(value: str | None) -> jdatetime.date | None:
    """Parse a stored Jalali ISO date, returning ``None`` for malformed data."""
    if not value:
        return None
    try:
        return jdatetime.date(*map(int, value.split("-")))
    except (ValueError, TypeError):
        return None


def is_paused(entry: dict, today: jdatetime.date) -> bool:
    """Return whether an entry's inclusive pause date covers *today*."""
    paused_until = parse_jalali_date(entry.get("paused_until"))
    return paused_until is not None and paused_until >= today
