# dailydriver/cli/day_view.py
"""Unified day view – shows today or any past/future day."""
import jdatetime
from datetime import datetime, timedelta
from dailydriver.core.database import get_connection_cm
from dailydriver.display.header import build_header_data
from dailydriver.display.display_utils import print_header
from dailydriver.ui.terminal_ui import current_ui
import re

def show_day(cmd=None):
    """Entry point: 'day', 'day -1', 'day 1405-02-15', 'today', or just a date string."""
    today = jdatetime.date.today()
    target = today
    is_today = True

    if cmd is not None:
        cmd = cmd.strip()
        parts = cmd.split(maxsplit=1)
        command = parts[0].lower() if parts else ''
        arg = parts[1].strip() if len(parts) > 1 else ''

        if command == 'today':
            _show_day_body(today, True)
            return

        # If no command recognised, treat the entire string as a possible date
        if command not in ('day', 'today') and cmd.count('-') == 2:
            arg = cmd
            command = 'day'

        if command == 'day' and arg:
            if arg.startswith('-'):
                try:
                    offset = int(arg)
                    target = today + jdatetime.timedelta(days=offset)
                except ValueError:
                    current_ui.print_line("Invalid offset. Use -1 for yesterday, etc.")
                    return
            else:
                try:
                    y, m, d = map(int, arg.split('-'))
                    target = jdatetime.date(y, m, d)
                except (ValueError, OverflowError):
                    current_ui.print_line("Invalid Jalali date. Use YYYY-MM-DD.")
                    return

    is_today = (target == today)

    # Day view loop
    while True:
        current_ui.clear()
        date_str = target.strftime('%Y-%m-%d')
        data = build_header_data(day=date_str, is_today=is_today)
        print_header(data)

        _show_day_body(target, is_today)

        current_ui.print_line("(p)rev  (n)ext  (q)uit  or YYYY-MM-DD")
        current_ui.print_line("n/p = next/prev day, 5n = 5 days")
        choice = current_ui.prompt("> ").strip().lower()

        if choice == 'q':
            break
        elif re.match(r'^\d{4}-\d{2}-\d{2}$', choice):
            try:
                y, m, d = map(int, choice.split('-'))
                target = jdatetime.date(y, m, d)
            except ValueError:
                current_ui.print_line("Invalid Jalali date.")
                current_ui.prompt("Press Enter to continue.")
        elif re.match(r'^\d*[np]$', choice):
            if choice[-1] == 'n':
                steps = int(choice[:-1]) if choice[:-1] else 1
                target = target + jdatetime.timedelta(days=steps)
            else:  # 'p'
                steps = int(choice[:-1]) if choice[:-1] else 1
                target = target - jdatetime.timedelta(days=steps)
        is_today = (target == today)

def _show_day_body(target, is_today):
    """Print naps, entries for a given date. (Prayers and sleep are in the header.)"""
    date_str = target.strftime('%Y-%m-%d')
    with get_connection_cm() as conn:
        cur = conn.cursor()

        # Date boundaries for entries (Gregorian)
        gdate = target.togregorian()
        gstart = datetime(gdate.year, gdate.month, gdate.day, 0, 0, 0)
        gend = gstart + timedelta(hours=24)

        # Entries
        current_ui.print_line("\n📝 Entries:")
        cur.execute("""
            SELECT e.id, e.description, e.created_at,
                   GROUP_CONCAT(DISTINCT c.path) AS cats
            FROM entries e
            LEFT JOIN entry_categories ec ON e.id = ec.entry_id
            LEFT JOIN categories c ON ec.category_id = c.id
            WHERE e.created_at BETWEEN ? AND ?
            GROUP BY e.id
            ORDER BY e.created_at ASC
        """, (int(gstart.timestamp()), int(gend.timestamp())))
        entries = cur.fetchall()
        if not entries:
            current_ui.print_line("   No entries.")
        else:
            for e in entries:
                dt = datetime.fromtimestamp(e['created_at'])
                time_str = dt.strftime('%H:%M')
                cats = e['cats'] or '(no category)'
                desc = (e['description'] or '')[:50].replace('\n', ' ')
                current_ui.print_line(f"   {time_str}  {cats}")
                if desc:
                    current_ui.print_line(f"         {desc}")
