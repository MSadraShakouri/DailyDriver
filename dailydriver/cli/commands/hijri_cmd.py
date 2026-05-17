# dailydriver/cli/commands/hijri_cmd.py
"""Command to view and adjust the global Hijri date offset."""
from datetime import date, timedelta
from hijridate import Gregorian as HijriGregorian
from dailydriver.utils.calendar_events import get_hijri_offset, set_hijri_offset
from dailydriver.ui.terminal_ui import current_ui

__all__ = ['hijri_command']

_MONTH_NAMES = [
    "Muharram", "Safar", "Rabi al-Awwal", "Rabi al-Thani",
    "Jumada al-Ula", "Jumada al-Thani", "Rajab", "Sha'ban",
    "Ramadan", "Shawwal", "Dhu al-Qa'dah", "Dhu al-Hijjah"
]

def hijri_command(*args):
    """Always show the interactive Hijri offset menu (arguments ignored)."""
    _show_menu()

def _show_menu():
    """Display a menu to choose Hijri offset."""
    today_g = date.today()
    raw_hijri = HijriGregorian.fromdate(today_g).to_hijri()
    current_offset = get_hijri_offset()

    # raw_hijri has .year, .month, .day
    # We'll generate rows for offsets -2..+2
    offsets = [-2, -1, 0, 1, 2]
    current_ui.print_line(f"\nCurrent Hijri date (offset: {current_offset:+d}):")
    for off in offsets:
        g = today_g + timedelta(days=off)
        hijri_date = HijriGregorian.fromdate(g).to_hijri()
        month_name = _MONTH_NAMES[hijri_date.month - 1]
        line = f"  {hijri_date.day} {month_name}  ({off:+d})"
        if off == current_offset:
            line += "  ← current"
        current_ui.print_line(line)

    current_ui.print_line()
    choice = current_ui.prompt("Enter offset (-2, -1, 0, +1, +2) or q to quit: ").strip()
    if choice.lower() == 'q':
        return
    try:
        if choice.startswith('+') or choice.startswith('-'):
            offset = int(choice)
        else:
            offset = int(choice)
        if offset in offsets:
            set_hijri_offset(offset)
            current_ui.print_line(f"Offset set to {offset:+d}.")
        else:
            current_ui.print_line("Offset must be between -2 and +2.")
    except ValueError:
        current_ui.print_line("Invalid input.")
