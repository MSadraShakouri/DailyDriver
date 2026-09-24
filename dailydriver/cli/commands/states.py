"""Commands for starting and ending numbered category-injecting states."""

from __future__ import annotations

import re
from datetime import datetime

from dailydriver.core.journal import log_free_text
from dailydriver.core.state import clear_numbered_states, get_active_numbered_states, start_numbered_state
from dailydriver.ui.terminal_ui import current_ui

_START_RE = re.compile(r"^st([1-9])$", re.IGNORECASE)
_END_RE = re.compile(r"^et([1-9]+)$", re.IGNORECASE)


def _extract_update_last(parts: list[str]) -> tuple[list[str], bool]:
    """Remove the opt-in last-action flags, mirroring targets' ``-n`` helper."""
    update_last = False
    remaining: list[str] = []
    for part in parts:
        if part in ("-u", "--update-last"):
            update_last = True
        else:
            remaining.append(part)
    return remaining, update_last


def start_numbered_state_cmd(line: str):
    """Start one slot (``st1`` through ``st9``) with one or more categories."""
    parts = line.strip().split()
    if not parts:
        return "Usage: st1 <category...> [-u]"
    match = _START_RE.fullmatch(parts[0])
    if not match:
        return "State command must be st1 through st9."

    state_id = int(match.group(1))
    categories, update_last = _extract_update_last(parts[1:])
    if not categories:
        return f"Usage: st{state_id} <category...> [-u]"

    try:
        timestamp = start_numbered_state(state_id, categories, update_last=update_last)
    except (RuntimeError, ValueError) as error:
        return str(error)

    category_text = ", ".join(category.lower() for category in categories)
    result = f"State {state_id} started at {datetime.fromtimestamp(timestamp).strftime('%H:%M')} with: {category_text}"
    if update_last:
        result += " (last action updated)"
    return result


def end_numbered_states_cmd(line: str):
    """End a sequence of slots; the first slot anchors an optional final log."""
    parts = line.strip().split(maxsplit=1)
    if not parts:
        return "Usage: et<state numbers> [text] (for example: et31 arrived)"
    match = _END_RE.fullmatch(parts[0])
    if not match:
        return "Usage: et<state numbers> [text] (state numbers are 1-9)"

    state_ids = [int(char) for char in match.group(1)]
    if len(set(state_ids)) != len(state_ids):
        return "Each state number may appear only once."

    active_by_id = {state["id"]: state for state in get_active_numbered_states()}
    inactive = [state_id for state_id in state_ids if state_id not in active_by_id]
    if inactive:
        return f"State(s) {', '.join(map(str, inactive))} are not active."

    text = parts[1].strip() if len(parts) > 1 else ""
    if not text:
        clear_numbered_states(state_ids)
        return f"State(s) {', '.join(map(str, state_ids))} ended without logging."

    # A single journal row has one start time. The first number is deliberately
    # the anchor; the remaining numbers identify other states to close.
    started_at = active_by_id[state_ids[0]]["started_at"]
    result = log_free_text(text, started_at=started_at)
    if result is None:
        current_ui.print_line(f"Log cancelled — state(s) {', '.join(map(str, state_ids))} are still active.")
        return None

    clear_numbered_states(state_ids)
    return result
