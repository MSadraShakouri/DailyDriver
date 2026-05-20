# dailydriver/display/header/events.py
"""Great event, running event, and last action time header lines."""

from datetime import datetime

from dailydriver.core.logger import (
    get_active_great_event,
    get_last_action_time,
    get_pending_start,
)


def get_great_event_str(is_today):
    if not is_today:
        return ""
    active = get_active_great_event()
    if active:
        start_ts, cats = active
        time_str = datetime.fromtimestamp(start_ts).strftime("%H:%M")
        return f"⏱ Great Event [{', '.join(cats)}] since {time_str}"
    return ""


def get_running_event_str(is_today):
    if not is_today:
        return ""
    ts = get_pending_start()
    if ts is not None:
        dt = datetime.fromtimestamp(ts)
        return f"⏱ Event running since {dt.strftime('%H:%M')}"
    return ""


def get_last_entry_time(is_today):
    if not is_today:
        return ""
    last_ts = get_last_action_time()
    if last_ts is not None:
        return datetime.fromtimestamp(last_ts).strftime("%H:%M")
    return ""
