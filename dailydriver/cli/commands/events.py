"""Commands for chaining and long-running events."""

from __future__ import annotations

import re
from datetime import datetime

from dailydriver.core.journal import log_free_text
from dailydriver.core.state import (
    STATE_IDS,
    clear_great_event,
    clear_numbered_states,
    clear_pending_start,
    get_active_great_event,
    get_last_action_time,
    get_pending_start,
    save_pending_start,
    start_great_event,
    update_last_action,
)
from dailydriver.ui.terminal_ui import current_ui

from .states import resolve_state_numbers

# ``ln`` accepts the same numbered suffix as ``et``: ``ln4`` chains from the last
# action *and* closes state 4. Digits outside the slot range (``ln0``, ``ln10``)
# still reach this handler through the compact-numbered dispatcher, so they are
# rejected explicitly rather than silently dropping the numbers.
_CHAIN_RE = re.compile(r"^ln(\d+)$", re.IGNORECASE)
_SLOT_DIGITS = frozenset(str(state_id) for state_id in STATE_IDS)


def log_event_end(cmd: str):
    started_at = get_pending_start()
    if started_at is None:
        return "No running event to end."
    text = cmd.strip().split(maxsplit=1)[1] if len(cmd.strip().split(maxsplit=1)) > 1 else ""
    result = log_free_text(text, started_at=started_at)
    if result is not None:
        clear_pending_start()
        return result
    # Logging was cancelled: the timer is intentionally left running so nothing
    # is lost, but say so explicitly — a silent no-op looks like a broken command.
    current_ui.print_line("Log cancelled — the running event is still active (ee to end, ce to cancel).")
    return None


def log_chain_now(line: str):
    """Chain an entry from ``last_action`` to now, optionally closing states.

    ``ln [text]`` chains from the last action. ``ln4 <text>`` chains from the
    same last action and then ends state 4; extra digits close extra slots
    (``ln1352``). Unlike ``et4`` — which anchors the entry at the state's own
    start — the numbered chain keeps ``ln`` timing, so it measures the gap since
    whatever was logged last while the state ran.

    The numbered form requires text: an accidental ``ln4`` must not silently
    close a state without a journal entry. States are only cleared once the
    entry is saved, and a cancelled confirmation leaves every slot active.
    """
    parts = line.strip().split(maxsplit=1)
    command = parts[0].lower() if parts else ""
    text = parts[1].strip() if len(parts) > 1 else ""

    state_ids: list[int] = []
    match = _CHAIN_RE.fullmatch(command)
    if match:
        digits = match.group(1)
        if any(digit not in _SLOT_DIGITS for digit in digits):
            return "Usage: ln<state numbers> <text> (state numbers are 1-9)"
        if not text:
            return f"Usage: {command} <text> (for example: ln4 arrived)"
        states, error = resolve_state_numbers(digits)
        if error is not None:
            return error
        state_ids = [state["id"] for state in states]

    last_ts = get_last_action_time()
    if last_ts is None:
        return "No previous action to chain from."

    result = log_free_text(text, started_at=last_ts)
    if result is None:
        if state_ids:
            current_ui.print_line(f"Log cancelled — state(s) {', '.join(map(str, state_ids))} are still active.")
        return None
    if state_ids:
        clear_numbered_states(state_ids)
    return result


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
    # Logging was cancelled: the great event is intentionally left active so the
    # entry isn't lost, but say so explicitly instead of silently doing nothing.
    current_ui.print_line("Log cancelled — the great event is still active (ege to end, cge to cancel).")
    return None


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
