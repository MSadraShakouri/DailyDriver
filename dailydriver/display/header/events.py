"""Great event, running event, and last action header lines."""

from __future__ import annotations

from datetime import datetime

from dailydriver.core.state import (
    get_active_great_event,
    get_active_numbered_states,
    get_last_action_time,
    get_pending_start,
)
from dailydriver.display.display_utils import display_width, get_width

# One numbered state per header line: "⏱ 3 friends/b food/lunch · 15:30".
_STATE_ICON = "⏱"
_STATE_TIME_SEPARATOR = "·"


def get_great_event_str(is_today: bool) -> str:
    if not is_today:
        return ""
    active = get_active_great_event()
    if active:
        start_ts, categories = active
        return f"⏱ Great Event [{', '.join(categories)}] since {datetime.fromtimestamp(start_ts).strftime('%H:%M')}"
    return ""


def _wrap_state_line(prefix: str, categories: list[str], tail: str) -> list[str]:
    """Lay out ``<prefix><categories> <tail>`` with a hanging indent.

    The generic :func:`wrap_line` splits on whitespace, which would strand the
    ``·`` at the end of a wrapped row and push the time onto its own line.
    Categories are placed word by word instead and the ``· HH:MM`` tail is kept
    as one unit, dropping to an indented row only when it truly cannot fit.

    Widths use ``>=`` like :func:`wrap_line`, leaving a column of slack for
    characters (the timer emoji among them) that terminals draw wider than
    :func:`display_width` measures them.
    """
    width = get_width()
    indent = " " * display_width(prefix)
    lines: list[str] = []
    line = prefix

    for category in categories:
        if line != prefix and display_width(line + category) >= width:
            lines.append(line.rstrip())
            line = indent
        line += category + " "

    # Keep the tail on the last category's row whenever it still fits.
    if line not in (prefix, indent) and display_width(line + tail) >= width:
        lines.append(line.rstrip())
        line = indent

    lines.append((line + tail).rstrip())
    return lines


def get_numbered_states_lines(is_today: bool) -> list[str]:
    """Return one compact header line per active numbered state, in slot order."""
    if not is_today:
        return []

    lines: list[str] = []
    for state in get_active_numbered_states():
        started = datetime.fromtimestamp(state["started_at"]).strftime("%H:%M")
        lines.extend(
            _wrap_state_line(
                f"{_STATE_ICON} {state['id']} ",
                state["categories"],
                f"{_STATE_TIME_SEPARATOR} {started}",
            )
        )
    return lines


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
