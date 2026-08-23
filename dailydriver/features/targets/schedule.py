"""Target recurrence calculations."""

import jdatetime

from dailydriver.features.presentation import is_paused
from dailydriver.utils.intervals import next_instance_date

from .history import get_daily_total, get_last_fulfilled_date


def get_last_fulfilled_date_for_entry(entry_id: int) -> jdatetime.date | None:
    """Return the latest date on which an entry met its interval goal."""
    return get_last_fulfilled_date(entry_id)


def get_daily_total_for_entry(entry_id: int, date: jdatetime.date) -> int:
    """Return progress logged for an entry on one Jalali date."""
    return get_daily_total(entry_id, date)


def compute_next_due(entry: dict, today: jdatetime.date, conn=None) -> jdatetime.date | None:
    """Compute the next due date for an entry based on its interval and last fulfilled date."""
    if is_paused(entry, today):
        return None

    if not entry.get("interval_type"):
        return None

    # Pass connection if available
    last_fulfilled = get_last_fulfilled_date(entry["id"], conn=conn)
    if last_fulfilled is None and entry.get("created_at"):
        ref_date = jdatetime.date.fromtimestamp(entry["created_at"])
    else:
        ref_date = today

    return next_instance_date(
        interval_type=entry["interval_type"],
        interval_value=str(entry["interval_value"]) if entry.get("interval_value") is not None else None,
        calendar="jalali",
        last_fulfilled_date=last_fulfilled,
        reference_date=ref_date,
    )
