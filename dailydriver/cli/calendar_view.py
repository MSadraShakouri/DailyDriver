# dailydriver/cli/calendar_view.py
"""Calendar command: shows a month grid and upcoming events."""
import jdatetime
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.calendar_events import get_events, get_upcoming_events

def show_calendar(args=None):
    """Entry point for 'cal' command."""
    if args is None:
        args = []
    year = None
    month = None
    if len(args) >= 1:
        try:
            month = int(args[0])
        except ValueError:
            month = None
    if len(args) >= 2:
        try:
            year = int(args[1])
        except ValueError:
            year = None
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

    # Print month grid
    _print_month_grid(year, month)

    # Print upcoming events
    events = get_events()
    upcoming = get_upcoming_events(events, days=15)
    if upcoming:
        current_ui.print_line("\n─── Upcoming 15 days ───")
        for date, e in upcoming:
            prefix = "🎌" if e.get("holiday") else "📌"
            current_ui.print_line(f"  {date.strftime('%d %B')}: {prefix} {e['title']}")
    else:
        current_ui.print_line("No events for the next 15 days.")

def _print_month_grid(year, month):
    """Print a simple calendar grid for a Jalali month."""
    # Get number of days in month
    if month <= 6:
        num_days = 31
    elif month <= 11:
        num_days = 30
    else:
        # Esfand: leap year detection (simplified)
        try:
            jdatetime.date(year, 12, 30)
            num_days = 30
        except ValueError:
            num_days = 29
    # Weekday of 1st
    first_day = jdatetime.date(year, month, 1)
    weekday = first_day.weekday()  # 0=Sat, 1=Sun, ..., 6=Fri
    # Persian week names
    days_header = "ش ی د س چ پ ج"
    current_ui.print_line(f"\n{first_day.strftime('%B %Y')}")
    current_ui.print_line(days_header)
    # Print leading spaces
    line = "   " * weekday
    for day in range(1, num_days + 1):
        # Highlight today
        today = jdatetime.date.today()
        is_today = (year == today.year and month == today.month and day == today.day)
        # Check if holiday (from events)
        events = get_events()
        holiday = False
        if events:
            for e in events:
                if e["month"] == month and e["day"] == day and e.get("holiday"):
                    holiday = True
                    break
        # Format day string
        if is_today:
            day_str = f"[{day:2d}]"
        elif holiday:
            day_str = f"*{day:2d}*"
        else:
            day_str = f" {day:2d} "
        line += day_str
        weekday += 1
        if weekday == 7:
            current_ui.print_line(line)
            line = ""
            weekday = 0
    if line:
        current_ui.print_line(line)
