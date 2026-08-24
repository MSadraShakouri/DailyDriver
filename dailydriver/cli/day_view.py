# dailydriver/cli/day_view.py
"""Unified day view – shows today or any past/future day."""

import re
from datetime import datetime, timedelta

import jdatetime

from dailydriver.cli.timeline import collect_timeline_items
from dailydriver.core.database import get_connection_cm
from dailydriver.core.state import (
    DAY_VIEW_MODE_DAY_START,
    DAY_VIEW_MODE_MIDNIGHT,
    get_day_start_hour,
    get_day_view_mode,
    set_day_view_mode,
)
from dailydriver.display.display_utils import pline_wrap
from dailydriver.display.header import build_header_data
from dailydriver.display.header_renderer import print_header
from dailydriver.ui.terminal_ui import current_ui


def show_day(cmd=None):
    """Entry point: 'day', 'day -1', 'day 1405-02-15', 'today', or just a date string."""
    today = jdatetime.date.today()
    target = today
    is_today = True

    if cmd is not None:
        cmd = cmd.strip()
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower() if parts else ""
        arg = parts[1].strip() if len(parts) > 1 else ""

        if command == "today":
            _show_day_body(today, get_day_view_mode())
            return

        # If no command recognised, treat the entire string as a possible date
        if command not in ("day", "today") and cmd.count("-") == 2:
            arg = cmd
            command = "day"

        if command == "day" and arg:
            if arg.startswith("-"):
                try:
                    offset = int(arg)
                    target = today + jdatetime.timedelta(days=offset)
                except ValueError:
                    current_ui.print_line("Invalid offset. Use -1 for yesterday, etc.")
                    return
            else:
                try:
                    y, m, d = map(int, arg.split("-"))
                    target = jdatetime.date(y, m, d)
                except (ValueError, OverflowError):
                    current_ui.print_line("Invalid Jalali date. Use YYYY-MM-DD.")
                    return

    is_today = target == today
    mode = get_day_view_mode()

    # Day view loop
    while True:
        current_ui.clear()
        date_str = target.strftime("%Y-%m-%d")
        data = build_header_data(day=date_str, is_today=is_today)
        print_header(data)

        _show_day_body(target, mode)

        if mode == DAY_VIEW_MODE_DAY_START:
            mode_label = f"day start ({get_day_start_hour():02d}:00)"
        else:
            mode_label = "midnight"
        current_ui.print_line(f"\033[1m(p)rev  (n)ext  (m)ode [{mode_label}]  (q)uit  or YYYY-MM-DD\033[0m")
        current_ui.print_line("\033[1mn/p = next/prev day, 5n = 5 days\033[0m")
        current_ui.print_line()
        choice = current_ui.prompt("> ").strip().lower()

        if choice == "q":
            break
        elif choice == "m":
            mode = DAY_VIEW_MODE_MIDNIGHT if mode == DAY_VIEW_MODE_DAY_START else DAY_VIEW_MODE_DAY_START
            set_day_view_mode(mode)
        elif re.match(r"^\d{4}-\d{2}-\d{2}$", choice):
            try:
                y, m, d = map(int, choice.split("-"))
                target = jdatetime.date(y, m, d)
            except ValueError:
                current_ui.print_line("Invalid Jalali date.")
                current_ui.prompt("Press Enter to continue.")
        elif re.match(r"^\d*[np]$", choice):
            if choice[-1] == "n":
                steps = int(choice[:-1]) if choice[:-1] else 1
                target = target + jdatetime.timedelta(days=steps)
            else:  # 'p'
                steps = int(choice[:-1]) if choice[:-1] else 1
                target = target - jdatetime.timedelta(days=steps)
        is_today = target == today


def _day_window(target, mode):
    """Return the [start, end] inclusive timestamp bounds for *target*.

    In midnight mode the day runs 00:00 → 24:00; in day-start mode it runs
    from the configured day-start hour to the same hour the next day.
    """
    gdate = target.togregorian()
    shift_hour = get_day_start_hour() if mode == DAY_VIEW_MODE_DAY_START else 0
    gstart = datetime(gdate.year, gdate.month, gdate.day) + timedelta(hours=shift_hour)
    gend = gstart + timedelta(hours=24)
    return int(gstart.timestamp()), int(gend.timestamp()) - 1


def _show_day_body(target, mode):
    """Print the unified timeline for a given date."""
    start, end = _day_window(target, mode)
    with get_connection_cm(auto=False) as conn:
        items = collect_timeline_items(conn, start, end)

    current_ui.print_line("\n📝 Timeline:")
    if not items:
        current_ui.print_line("   Nothing logged.")
        current_ui.print_line()
        return

    for item in items:
        # Time on its own line, label/categories on the next (both indented
        # deeper), description on the last (pulled back left).
        current_ui.print_line(f"    {item['display_time']}")
        pline_wrap(item["text"], indent=4)

        details = (item.get("details") or "").replace("\n", " ").strip()
        if details:
            pline_wrap(details, indent=2, max_lines=2)
        current_ui.print_line()
