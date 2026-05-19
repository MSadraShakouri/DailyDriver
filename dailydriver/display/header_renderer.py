# dailydriver/display/header_renderer.py
"""Renders the daily header dictionary to the terminal."""
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.display.display_utils import (
    get_width, display_width, pline, pline_wrap, spread_line, pline_center
)

# dailydriver/display/header_renderer.py
"""Renders the daily header dictionary to the terminal."""
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.display.display_utils import (
    get_width, display_width, pline, pline_wrap, spread_line, pline_center
)

def print_header(data: dict, add_separator: bool = True):
    """Print the daily header from a dictionary built by header_data.build()."""
    w = get_width()
    date_str = data['date_str']

    # Build the full prayer line using the prefix and parts
    prayer_str = spread_line(data['prayer_parts'], prefix="🕌 ")

    bday_str = data.get('bday_str', '')

    # New centered date block
    pline_center(data['jalali_line'])
    pline_center(data['separator'])
    current_ui.print_line(data['greg_hijri_line'])   # already centered by spread_line
    current_ui.print_line()                           # breather

    pline(prayer_str)

    sleep_str = data.get('sleep_str', '💤 —')
    nap_str = data.get('nap_str', '')
    if nap_str:
        combined = spread_line([sleep_str, nap_str])
        current_ui.print_line(combined)
    else:
        pline(sleep_str)

    weather_str = data.get('weather_str', '')
    if weather_str:
        pline(weather_str)

    # Great event
    if ge_str := data.get('great_event_str', ''):
        pline(ge_str)

    # Running event
    if event_str := data.get('event_str', ''):
        pline(event_str)

    if bday_str:
        pline(bday_str)
    for line in data.get('hygiene_lines', []):
        pline(line)

    # Prayer nudges
    for nudge in data.get('prayer_nudges', []):
        pline(nudge)

    current_ui.print_line()

    calendar_lines = data.get('calendar_lines', [])
    for line in calendar_lines:
        pline_wrap(line)
    reminders_str = data.get('reminders_str', '')
    if reminders_str:
        pline(reminders_str)

    current_ui.print_line()

    # Bottom bar (right‑aligned, total width = w // 3)
    total_bar_width = w // 5 * 2
    if data.get('is_today', True):
        last_time = data.get('last_entry_time', '')
        if last_time:
            suffix = " Last " + last_time
            dash_len = total_bar_width - display_width(suffix)
            if dash_len < 0:
                dash_len = 0
            visible = '─' * dash_len + suffix
            pad = w - display_width(visible)
            current_ui.print_line(' ' * pad + visible)
        else:
            dash_len = total_bar_width
            visible = '─' * dash_len
            pad = w - display_width(visible)
            current_ui.print_line(' ' * pad + visible)
    else:
        dash_len = total_bar_width
        visible = '─' * dash_len
        pad = w - display_width(visible)
        current_ui.print_line(' ' * pad + visible)

    if add_separator:
        current_ui.print_line()   # blank line before prompt (REPL only)
