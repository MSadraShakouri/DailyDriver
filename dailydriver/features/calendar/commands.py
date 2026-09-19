from datetime import date, timedelta

from dailydriver.cli.calendar_view import show_calendar  # noqa: F401 (re‑exported)
from dailydriver.cli.year_view import show_year  # noqa: F401 (re‑exported)
from dailydriver.features.calendar.converter import (
    gregorian_to_hijri,
    gregorian_to_hijri_with_month_offsets,
)
from dailydriver.features.calendar.hijri import get_hijri_offset  # noqa: F401 (legacy re-export)
from dailydriver.features.calendar.hijri import set_hijri_offset  # noqa: F401 (legacy re-export)
from dailydriver.features.calendar.hijri import (
    get_hijri_month_offset,
    set_hijri_month_offset,
)
from dailydriver.ui.terminal_ui import current_ui  # noqa: F401 (re‑exported)

_MONTH_NAMES = [
    "Muharram",
    "Safar",
    "Rabi al-Awwal",
    "Rabi al-Thani",
    "Jumada al-Ula",
    "Jumada al-Thani",
    "Rajab",
    "Sha'ban",
    "Ramadan",
    "Shawwal",
    "Dhu al-Qa'dah",
    "Dhu al-Hijjah",
]


def hijri_command(*args):
    """Show the interactive offset menu for today's Hijri month."""
    _show_menu()


def _show_menu():
    """Display a menu to choose Hijri offset."""
    today_g = date.today()
    current_hijri = gregorian_to_hijri_with_month_offsets(today_g, get_hijri_month_offset)
    current_offset = get_hijri_month_offset(current_hijri.year, current_hijri.month)

    # The choices are now stored for this Hijri month only.  The offset sign
    # remains compatible with the original command: -1 moves a boundary one
    # Gregorian day later.
    offsets = [-2, -1, 0, 1, 2]
    current_ui.print_line(
        f"\nCurrent Hijri date (offset for {current_hijri.year}/{current_hijri.month}: {current_offset:+d}):"
    )
    for off in offsets:
        g = today_g + timedelta(days=off)
        hijri_date = gregorian_to_hijri(g)
        month_name = _MONTH_NAMES[hijri_date.month - 1]
        line = f"  {hijri_date.day} {month_name}  ({off:+d})"
        if off == current_offset:
            line += "  ← current"
        current_ui.print_line(line)

    current_ui.print_line()
    choice = current_ui.prompt("Enter offset (-2, -1, 0, +1, +2) or q to quit: ").strip()
    if choice.lower() == "q":
        return
    try:
        if choice.startswith("+") or choice.startswith("-"):
            offset = int(choice)
        else:
            offset = int(choice)
        if offset in offsets:
            set_hijri_month_offset(current_hijri.year, current_hijri.month, offset)
            current_ui.print_line(f"Offset for {current_hijri.year}/{current_hijri.month} set to {offset:+d}.")
        else:
            current_ui.print_line("Offset must be between -2 and +2.")
    except ValueError:
        current_ui.print_line("Invalid input.")
