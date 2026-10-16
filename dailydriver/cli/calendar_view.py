# dailydriver/cli/calendar_view.py
"""Calendar command: shows a clean month grid and upcoming events."""

import jdatetime

from dailydriver.ui.terminal_ui import current_ui

# NOTE: ``features.calendar.catalog`` is imported lazily inside
# :func:`show_calendar` because ``features.calendar.commands`` re-exports this
# module — a top-level import would be circular.

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


def _normalize_args(line=None) -> list[str]:
    """Normalize dispatcher input to an argument list.

    The dispatcher calls handlers with the full command line string
    (e.g. ``\"cal 6 1405\"``), while older callers/tests may pass a list
    of arguments directly. Both forms are accepted here.
    """
    if line is None:
        return []
    if isinstance(line, str):
        parts = line.strip().split()
        # Drop the command token itself when present (``cal 6`` -> ``[6]``),
        # but tolerate a bare argument string (``6`` -> ``[6]``).
        if parts and parts[0].lower() == "cal":
            return parts[1:]
        return parts
    return [str(part) for part in line]


def _parse_month(token: str) -> int | None:
    """Parse a month number (1-12) or English month name/abbreviation."""
    token = token.strip().lower()
    if token.isdigit():
        month = int(token)
        return month if 1 <= month <= 12 else None
    for index, name in enumerate(_JALALI_MONTHS_EN, 1):
        if token == name.lower() or token == name.lower()[:3]:
            return index
    return None


def show_calendar(line=None):
    args = _normalize_args(line)
    year = None
    month = None
    if len(args) >= 1:
        month = _parse_month(args[0])
    if len(args) >= 2:
        try:
            year = int(args[1])
        except ValueError:
            year = None
    if month is None and args:
        # A present-but-unparseable month (e.g. ``cal 13`` or ``cal foo``)
        # is an error, while a bare ``cal`` falls back to the current month.
        current_ui.print_line("Invalid month (1-12).")
        return
    if month is None:
        today = jdatetime.date.today()
        month = today.month
        if year is None:
            year = today.year
    if year is None:
        year = jdatetime.date.today().year
    if not (1 <= month <= 12):
        current_ui.print_line("Invalid month (1-12).")
        return

    _print_month_grid(year, month)

    from dailydriver.features.calendar.catalog import get_events, get_upcoming_events

    events = get_events()
    upcoming = get_upcoming_events(events, days=15)
    if upcoming:
        current_ui.print_line("\n─── Upcoming 15 days ───")
        cal_icons = {"jalali": "🔆", "gregorian": "🌐", "hijri": "🌙"}
        holiday_icon = "🎊"
        for date, e in upcoming:
            cal = e.get("calendar", "jalali")
            prefix = cal_icons.get(cal, "📌")
            if e.get("holiday"):
                prefix += holiday_icon
            current_ui.print_line(f"  {date.strftime('%d %B')}: {prefix} {e['title_en']}")
    else:
        current_ui.print_line("No events for the next 15 days.")


def _print_month_grid(year, month):
    """Print a clean, properly aligned Jalali month grid (Unix cal style)."""
    month_name = _JALALI_MONTHS_EN[month - 1]
    header = f"{month_name} {year}"
    grid_width = 20  # 7*2 + 6 spaces

    current_ui.print_line(header.center(grid_width))
    current_ui.print_line("Sa Su Mo Tu We Th Fr")

    first_day = jdatetime.date(year, month, 1)
    # weekday: 0=Sat, 6=Fri
    start_col = first_day.weekday()

    # month length
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

    days = []
    # leading blanks
    for _ in range(start_col):
        days.append("  ")  # two spaces per empty cell

    today = jdatetime.date.today()
    for day in range(1, num_days + 1):
        if year == today.year and month == today.month and day == today.day:
            days.append(f"\033[7m{day:2d}\033[0m")
        else:
            days.append(f"{day:2d}")

    # print rows of 7
    for i in range(0, len(days), 7):
        row = " ".join(days[i : i + 7])
        current_ui.print_line(row)
