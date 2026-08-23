"""Great event, running event, and last action header lines."""

from __future__ import annotations

from datetime import datetime

from dailydriver.core.state import get_active_great_event, get_last_action_time, get_pending_start


def get_great_event_str(is_today: bool) -> str:
    if not is_today:
        return ""
    active = get_active_great_event()
    if active:
        start_ts, categories = active
        return f"⏱ Great Event [{', '.join(categories)}] since {datetime.fromtimestamp(start_ts).strftime('%H:%M')}"
    return ""


def get_running_event_str(is_today: bool) -> str:
    if not is_today:
        return ""
    timestamp = get_pending_start()
    if timestamp is not None:
        return f"⏱ Event running since {datetime.fromtimestamp(timestamp).strftime('%H:%M')}"
    return ""


def get_last_entry_time(is_today: bool) -> str:
    if not is_today:
        return ""
    timestamp = get_last_action_time()
    return datetime.fromtimestamp(timestamp).strftime("%H:%M") if timestamp is not None else ""
