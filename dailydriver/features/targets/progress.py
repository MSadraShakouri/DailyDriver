"""Progress logging for finite and indefinite targets."""

import time

from . import clock
from .entries import get_entry_by_name, record_progress


def log_progress(name: str, amount: int, expected_kind: str | None = None) -> str:
    """Log progress for an entry by name.
    If expected_kind is set, it validates the entry kind matches.
    Returns a confirmation string.
    """
    if amount <= 0:
        return "Amount must be positive."

    entry = get_entry_by_name(name)
    if not entry:
        return f"Entry not found: {name}"

    if expected_kind and entry["kind"] != expected_kind:
        return f"'{name}' is a {entry['kind']}, not a {expected_kind}."

    today = clock.today()
    entry_id = entry["id"]
    target = entry["target_total"]
    current_logged = entry["logged_total"]

    # Calculate new total (cap at target if finite)
    new_total = current_logged + amount
    if target is not None and new_total > target:
        new_total = target

    actual_amount = new_total - current_logged
    if actual_amount <= 0:
        return "Already at target. Nothing to log."

    record_progress(entry_id, actual_amount, new_total, today.strftime("%Y-%m-%d"), int(time.time()))

    # Build confirmation
    total_display = f"{new_total}/{target}" if target is not None else f"{new_total}/∞"
    if target is not None and target > 0:
        pct = (new_total / target) * 100
        return f"{name}: {total_display} ({pct:.1f}%)"
    else:
        return f"{name}: {total_display}"
