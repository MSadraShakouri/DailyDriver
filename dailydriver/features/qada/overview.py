"""Build manager-ready qada progress records."""

import jdatetime

from dailydriver.features.presentation import is_paused

from .entries import add_entry, get_entry_by_slot_or_kind
from .schedule import compute_pending_instance


def get_all_entries_with_progress(today=None):
    """Return all 4 qada entries in fixed order with progress computed."""
    if today is None:
        today = jdatetime.date.today()

    # Define the 4 entries
    entry_defs = [
        {"slot": "fajr", "kind": "prayer", "name": "Fajr"},
        {"slot": "dhuhr_asr", "kind": "prayer", "name": "Dhuhr/Asr"},
        {"slot": "maghrib_isha", "kind": "prayer", "name": "Maghrib/Isha"},
        {"slot": None, "kind": "fasting", "name": "Fasting"},
    ]

    result = []
    for idx, defn in enumerate(entry_defs, 1):
        entry = get_entry_by_slot_or_kind(slot=defn["slot"], kind=defn["kind"])
        if entry is None:
            # Create with defaults
            name = defn["name"]
            _ = add_entry(
                name=name,
                kind=defn["kind"],
                slot=defn["slot"],
                interval_type="daily",
                target_total=-1,
            )
            entry = get_entry_by_slot_or_kind(slot=defn["slot"], kind=defn["kind"])
            if entry is None:
                # Fallback: shouldn't happen
                continue

        # Compute progress
        target = entry.get("target_total", -1)
        logged = entry.get("logged_total", 0)
        if target == -1:
            progress_display = "Not set"
            percentage = None
            is_complete = False
        elif target == 0:
            progress_display = "0/0"
            percentage = 0.0
            is_complete = True
        else:
            pct = (logged / target) * 100
            percentage = pct  # raw float
            progress_display = f"{logged}/{target}"
            is_complete = logged >= target

        # Check paused
        paused_until = entry.get("paused_until")
        entry_is_paused = is_paused(entry, today)

        # Compute next instance
        next_instance = None
        if not is_complete and target > 0 and not entry_is_paused:
            next_instance = compute_pending_instance(entry, today)

        result.append(
            {
                "id": entry["id"],
                "index": idx,
                "name": defn["name"],
                "kind": defn["kind"],
                "slot": defn["slot"],
                "target_total": target,
                "logged_total": logged,
                "progress_display": progress_display,
                "percentage": percentage,
                "is_complete": is_complete,
                "is_paused": entry_is_paused,
                "next_instance": next_instance,
                "interval_type": entry.get("interval_type"),
                "interval_value": entry.get("interval_value"),
                "paused_until": paused_until,
            }
        )

    return result
