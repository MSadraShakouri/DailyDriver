# dailydriver/display/header_renderer.py
"""Renders the daily header dictionary to the terminal."""

from dailydriver.display.display_utils import (
    display_width,
    get_width,
    pline,
    pline_center,
    pline_wrap,
    spread_line,
    wrap_line,
)
from dailydriver.ui.terminal_ui import current_ui

# dailydriver/display/header_renderer.py
"""Renders the daily header dictionary to the terminal."""


def print_header(data: dict, add_separator: bool = True):
    """Print the daily header from a dictionary built by header_data.build()."""
    w = get_width()

    # Build the full prayer line using the prefix and parts
    prayer_str = spread_line(data["prayer_parts"], prefix="🕌 ")

    # New centered date block
    pline_center(data["jalali_line"])
    pline_center(data["separator"])
    current_ui.print_line(data["greg_hijri_line"])  # already centered by spread_line
    current_ui.print_line()  # breather

    pline(prayer_str)

    sleep_str = data.get("sleep_str", "💤 —")
    nap_str = data.get("nap_str", "")
    if nap_str:
        combined = spread_line([sleep_str, nap_str])
        current_ui.print_line(combined)
    else:
        pline(sleep_str)

    weather_str = data.get("weather_str", "")
    if weather_str:
        pline(weather_str)

    # Great event
    if ge_str := data.get("great_event_str", ""):
        pline(ge_str)

    # Running event
    if event_str := data.get("event_str", ""):
        pline(event_str)

    for line in data.get("bday_lines", []):
        pline(line)

    for line in data.get("hygiene_lines", []):
        pline(line)

    # Prayer nudges
    for nudge in data.get("prayer_nudges", []):
        pline(nudge)

    # Event reminders
    event_reminder_lines = data.get("event_reminder_lines", [])
    if event_reminder_lines:
        current_ui.print_line()
        for item in event_reminder_lines:
            if isinstance(item, tuple):
                prefix, title = item
                indent = " " * display_width(prefix)
                wrap_line(prefix, title, indent)
            else:
                pline(item)

    # Tomorrow preview
    tomorrow_lines = data.get("tomorrow_lines", [])
    if tomorrow_lines:
        current_ui.print_line()
        pline(tomorrow_lines[0])
        for item in tomorrow_lines[1:]:
            if isinstance(item, tuple):
                prefix, title = item
                indent = " " * display_width(prefix)
                wrap_line(prefix, title, indent)
            else:
                pline(item)

    # Calendar events
    calendar_lines = data.get("calendar_lines", [])
    if calendar_lines:
        current_ui.print_line()
        for item in calendar_lines:
            if isinstance(item, tuple):
                prefix, title = item
                indent = " " * display_width(prefix)
                wrap_line(prefix, title, indent)
            else:
                pline(item)

    # Old reminders string (if still used)
    reminders_str = data.get("reminders_str", "")
    if reminders_str:
        pline(reminders_str)

    # Bottom bar (already present, don't add extra blank line)

    current_ui.print_line()

    # Bottom bar (right‑aligned, total width = w // 3)
    total_bar_width = w // 5 * 2
    if data.get("is_today", True):
        last_time = data.get("last_entry_time", "")
        if last_time:
            suffix = " Last " + last_time
            dash_len = total_bar_width - display_width(suffix)
            if dash_len < 0:
                dash_len = 0
            visible = "─" * dash_len + suffix
            pad = w - display_width(visible)
            current_ui.print_line(" " * pad + visible)
        else:
            dash_len = total_bar_width
            visible = "─" * dash_len
            pad = w - display_width(visible)
            current_ui.print_line(" " * pad + visible)
    else:
        dash_len = total_bar_width
        visible = "─" * dash_len
        pad = w - display_width(visible)
        current_ui.print_line(" " * pad + visible)

    if add_separator:
        current_ui.print_line()  # blank line before prompt (REPL only)
