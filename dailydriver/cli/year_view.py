# dailydriver/cli/year_view.py
"""Responsive year calendar view (like cal -y) for DailyDriver."""

import shutil

import jdatetime

from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.calendar_events import get_events

_JALALI_MONTHS_EN = [
    "Farvardin",
    "Ordibehesht",
    "Khordad",
    "Tir",
    "Mordad",
    "Shahrivar",
    "Mehr",
    "Aban",
    "Azar",
    "Dey",
    "Bahman",
    "Esfand",
]


def _build_month_lines(year, month, today=None):
    """Return a list of strings representing one month's clean grid.
    Each line is exactly 20 characters wide (7*2 + 6 spaces).
    """
    first_day = jdatetime.date(year, month, 1)
    start_col = first_day.weekday()  # 0=Sat
    if month <= 6:
        num_days = 31
    elif month <= 11:
        num_days = 30
    else:
        try:
            jdatetime.date(year, 12, 30)
            num_days = 30
        except ValueError:
            num_days = 29

    lines = []
    # centered month name
    month_name = _JALALI_MONTHS_EN[month - 1]
    lines.append(month_name.center(20))
    # weekday header
    lines.append("Sa Su Mo Tu We Th Fr")

    # day cells
    day_cells = ["  "] * start_col

    for day in range(1, num_days + 1):
        if today and year == today.year and month == today.month and day == today.day:
            day_cells.append(f"\033[7m{day:2d}\033[0m")
        else:
            day_cells.append(f"{day:2d}")

    # wrap into rows of 7
    for i in range(0, len(day_cells), 7):
        row = " ".join(day_cells[i : i + 7])
        # pad row to exactly 20 chars for consistent alignment
        row = row.ljust(20)
        lines.append(row)

    # pad to same height (6 data lines minimum)
    while len(lines) < 6:
        lines.append(" " * 20)
    return lines


def show_year():
    """Display a responsive year calendar."""
    try:
        term_width = shutil.get_terminal_size().columns
    except Exception:
        term_width = 80

    # each month grid is 20 chars + 2 spaces between grids
    if term_width >= 70:
        months_per_row = 3
    elif term_width >= 50:
        months_per_row = 2
    else:
        months_per_row = 1

    today = jdatetime.date.today()
    year = today.year

    raw_events = get_events() or []
    # Build list of holidays
    holidays = []
    for jdate, ev in raw_events:
        if ev.get("holiday"):
            holidays.append((jdate.month, jdate.day, ev))

    # Print the year header
    current_ui.print_line(f"\n{str(year).center(months_per_row * 22)}")
    current_ui.print_line()

    # Print months in rows
    for row_start in range(1, 13, months_per_row):
        months = list(range(row_start, min(row_start + months_per_row, 13)))
        grids = [_build_month_lines(year, m, today) for m in months]

        # Pad all grids to same number of lines
        max_lines = max(len(g) for g in grids)
        for g in grids:
            while len(g) < max_lines:
                g.append(" " * 20)

        # Print side by side with 2-space gap
        for line_idx in range(max_lines):
            line = "   ".join(g[line_idx] for g in grids)
            current_ui.print_line(line)
        current_ui.print_line()  # blank line between rows

    # List official holidays below
    if holidays:
        current_ui.print_line("─── تعطیلات رسمی ───")
        holidays.sort(key=lambda h: (h[0], h[1]))
        cal_icons = {"jalali": "🔆", "gregorian": "🌐", "hijri": "🌙"}
        holiday_icon = "🎊"
        for m, d, ev in holidays:
            cal = ev.get("calendar", "jalali")
            prefix = cal_icons.get(cal, "📌") + holiday_icon
            current_ui.print_line(f"  {m:02d}/{d:02d}  {prefix} {ev['title_en']}")
