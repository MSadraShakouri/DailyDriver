"""Commands for chaining and long-running events."""

from datetime import datetime

from dailydriver.core.logger import log_free_text
from dailydriver.ui.terminal_ui import current_ui

from .state import (
    clear_great_event,
    clear_pending_start,
    get_active_great_event,
    get_last_action_time,
    get_pending_start,
    start_great_event,
)

def log_event_end(cmd):
    started_at = get_pending_start()
    if started_at is None:
        return "No running event to end."

    parts = cmd.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""

    result = log_free_text(text, started_at=started_at)
    if result is not None:
        clear_pending_start()
        return result
    return None


def log_chain_now(line):
    last_ts = get_last_action_time()
    if last_ts is None:
        return "No previous action to chain from."

    parts = line.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""
    return log_free_text(text, started_at=last_ts)


def start_great_event_cmd(line):
    if get_active_great_event() is not None:
        current_ui.print_line("A great event is already active. Cancel it first (cge).")
        return None

    parts = line.strip().split(maxsplit=1)
    if len(parts) > 1:
        cat_str = parts[1].strip()
        cats = cat_str.split() if cat_str else []
    else:
        cat_input = current_ui.prompt("Great event categories (space‑separated): ").strip()
        cats = cat_input.split() if cat_input else []

    if not cats:
        current_ui.print_line("No categories entered. Great event not started.")
        return None

    cats = [c.lower() for c in cats]
    try:
        ts = start_great_event(cats)
    except RuntimeError as e:
        current_ui.print_line(str(e))
        return None

    time_str = datetime.fromtimestamp(ts).strftime("%H:%M")
    return f"Great event started at {time_str} with: {', '.join(cats)}"


def end_great_event_cmd(line):
    ge = get_active_great_event()
    if ge is None:
        current_ui.print_line("No great event is active.")
        return None
    start_ts, _ = ge

    parts = line.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""

    result = log_free_text(text, started_at=start_ts)

    if result is not None:
        clear_great_event()
    return result


def cancel_great_event_cmd(_=None):
    ge = get_active_great_event()
    if ge is None:
        current_ui.print_line("No great event active.")
        return None
    clear_great_event()
    return "Great event cancelled."
