"""Commands for chaining and long-running events."""

from __future__ import annotations

from datetime import datetime

from dailydriver.core.journal import log_free_text
from dailydriver.core.state import (
    clear_great_event,
    clear_pending_start,
    get_active_great_event,
    get_last_action_time,
    get_pending_start,
    save_pending_start,
    start_great_event,
    update_last_action,
)
from dailydriver.ui.terminal_ui import current_ui


def log_event_end(cmd: str):
    started_at = get_pending_start()
    if started_at is None:
        return "No running event to end."
    text = cmd.strip().split(maxsplit=1)[1] if len(cmd.strip().split(maxsplit=1)) > 1 else ""
    result = log_free_text(text, started_at=started_at)
    if result is not None:
        clear_pending_start()
        return result
    return None


def log_chain_now(line: str):
    last_ts = get_last_action_time()
    if last_ts is None:
        return "No previous action to chain from."
    text = line.strip().split(maxsplit=1)[1] if len(line.strip().split(maxsplit=1)) > 1 else ""
    return log_free_text(text, started_at=last_ts)


def start_great_event_cmd(line: str):
    if get_active_great_event() is not None:
        current_ui.print_line("A great event is already active. Cancel it first (cge).")
        return None

    parts = line.strip().split(maxsplit=1)
    if len(parts) > 1:
        cats = parts[1].strip().split()
    else:
        cats = current_ui.prompt("Great event categories (space‑separated): ").strip().split()

    if not cats:
        current_ui.print_line("No categories entered. Great event not started.")
        return None

    categories = [category.lower() for category in cats]
    try:
        timestamp = start_great_event(categories)
    except RuntimeError as error:
        current_ui.print_line(str(error))
        return None
    return f"Great event started at {datetime.fromtimestamp(timestamp).strftime('%H:%M')} with: {', '.join(categories)}"


def end_great_event_cmd(line: str):
    active = get_active_great_event()
    if active is None:
        current_ui.print_line("No great event is active.")
        return None
    started_at, _ = active
    text = line.strip().split(maxsplit=1)[1] if len(line.strip().split(maxsplit=1)) > 1 else ""
    result = log_free_text(text, started_at=started_at)
    if result is not None:
        clear_great_event()
    return result


def cancel_great_event_cmd(_=None):
    if get_active_great_event() is None:
        current_ui.print_line("No great event active.")
        return None
    clear_great_event()
    return "Great event cancelled."


__all__ = [
    "cancel_great_event_cmd",
    "end_great_event_cmd",
    "log_chain_now",
    "log_event_end",
    "save_pending_start",
    "start_great_event_cmd",
    "update_last_action",
]
