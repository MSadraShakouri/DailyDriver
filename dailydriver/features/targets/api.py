"""Public domain operations for targets.

The implementation is split by responsibility; this module is only a stable
import surface for callers that need several capabilities.
"""

from .commands import handle_counter_reset, handle_counter_total, handle_daily_total, handle_log_command
from .entries import (
    add_entry,
    delete_entry,
    edit_entry,
    get_all_entries,
    get_entry_by_id,
    get_entry_by_name,
    toggle_pause,
)
from .progress import log_progress
from .schedule import compute_next_due, get_daily_total_for_entry, get_last_fulfilled_date_for_entry

__all__ = [
    "add_entry",
    "compute_next_due",
    "delete_entry",
    "edit_entry",
    "get_all_entries",
    "get_daily_total_for_entry",
    "get_entry_by_id",
    "get_entry_by_name",
    "get_last_fulfilled_date_for_entry",
    "handle_counter_reset",
    "handle_counter_total",
    "handle_daily_total",
    "handle_log_command",
    "log_progress",
    "toggle_pause",
]
