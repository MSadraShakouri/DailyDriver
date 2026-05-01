# dailydriver/cli/year_view.py
"""Year calendar view for DailyDriver."""
import jdatetime
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.calendar_events import get_events

# Days in each month (1..12). For Esfand we handle leap years separately.
_MONTH_DAYS = [31, 31, 31, 31, 31, 31, 30, 30, 30, 30, 30, 29]

def _is_jalali_leap(year):
    """Return True if the given Jalali year is a leap year (i.e., Esfand has 30 days)."""
    # In the Jalali calendar, a year is leap if the remainder after dividing
    # (year + 2346) by 2820 is <= 1386?  Simpler: just check if 12/30 exists.
    try:
        jdatetime.date(year, 12, 30)
        return True
    except ValueError:
        return False

def _days_in_month(year, month):
    if month <= 11:
        return _MONTH_DAYS[month-1]
    # Esfand
    return 30 if _is_jalali_leap(year) else 29

def show_year():
    """Display a compact year calendar with events."""
    raw_events = get_events() or []   # returns list of (jalali_date, event_dict)
    today = jdatetime.date.today()
    current_year = today.year

    # Build lookup: (month, day) -> event (prefer holiday)
    event_map = {}
    for jdate, ev in raw_events:
        key = (jdate.month, jdate.day)
        if key not in event_map or (ev.get("holiday") and not event_map[key].get("holiday")):
            event_map[key] = ev

    # List of all holidays as (month, day, event)
    holidays = []
    for jdate, ev in raw_events:
        if ev.get("holiday"):
            holidays.append((jdate.month, jdate.day, ev))

    # Print header
    current_ui.print_line(f"\n══════ سال {current_year} هجری شمسی ══════")
    current_ui.print_line("  ● = holiday   ○ = other event\n")

    # Print months in rows of 3
    for row_start in range(0, 12, 3):
        months = [m for m in range(row_start+1, min(row_start+4, 13))]
        grids = []
        for month in months:
            grid = _build_month_grid(current_year, month, today, event_map)
            grids.append(grid)
        # Pad all grids to same height
        max_lines = max(len(g) for g in grids)
        for g in grids:
            while len(g) < max_lines:
                g.append(" " * 20)
        # Print side by side
        for line_idx in range(max_lines):
            line = "   ".join(grids[i][line_idx] for i in range(len(grids)))
            current_ui.print_line(line)
        current_ui.print_line()

    # List all holidays
    if holidays:
        current_ui.print_line("─── تعطیلات رسمی ───")
        holidays.sort(key=lambda h: (h[0], h[1]))  # sort by month,day
        for m, d, ev in holidays:
            current_ui.print_line(f"  {m:02d}/{d:02d}  {ev['title']}")

def _build_month_grid(year, month, today, event_map):
    """Return list of strings representing one month's grid."""
    first_day = jdatetime.date(year, month, 1)
    num_days = _days_in_month(year, month)
    weekday_of_first = first_day.weekday()  # 0=Sat, 6=Fri

    lines = []
    month_name = first_day.strftime("%B")
    lines.append(f"{month_name:^20}")
    lines.append("ش  ی  د  س  چ  پ  ج")

    day_cells = []
    # Leading spaces
    for _ in range(weekday_of_first):
        day_cells.append("   ")

    for d in range(1, num_days+1):
        key = (month, d)
        ev = event_map.get(key)
        if key == (today.month, today.day):
            cell = f"[{d:2d}]"
        elif ev and ev.get("holiday"):
            cell = f"●{d:2d}●"
        elif ev:
            cell = f"○{d:2d}○"
        else:
            cell = f" {d:2d} "
        day_cells.append(cell)

    # Wrap into lines of 7 cells
    for i in range(0, len(day_cells), 7):
        lines.append(" ".join(day_cells[i:i+7]))

    return lines