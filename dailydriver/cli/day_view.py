# dailydriver/cli/day_view.py
"""Unified day view – shows today or any past day."""
import jdatetime
from datetime import datetime, timedelta
from dailydriver.core.database import get_connection_cm
from dailydriver.display.header import build_header_data
from dailydriver.display.display_utils import print_header
from dailydriver.ui.terminal_ui import current_ui

def show_day(cmd=None):
    """Entry point: 'day', 'day -1', 'day 1405-02-15', 'today', or just a date string."""
    today = jdatetime.date.today()
    target = today
    is_past = False

    if cmd is not None:
        cmd = cmd.strip()
        # If the entire string is a Jalali date (contains two hyphens), use it directly
        if cmd.count('-') == 2:
            arg = cmd
            command = None
        else:
            parts = cmd.split(maxsplit=1)
            command = parts[0].lower()
            if command == 'today':
                # Show today’s detail without extra header
                _show_day_body(today, False)
                return
            else:
                if len(parts) > 1:
                    arg = parts[1].strip()
                else:
                    arg = None

        if command != 'today' and arg is not None:
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

    if target != today:
        is_past = True

    # Past‑day view: clear screen, draw adapted header and body, then allow navigation
    while True:
        current_ui.clear()
        date_str = target.strftime('%Y-%m-%d')
        data = build_header_data(day=date_str, is_past=is_past)
        print_header(data)

        _show_day_body(target, is_past)

        current_ui.print_line("(p)rev  (n)ext  (q)uit")
        choice = current_ui.prompt("> ").strip().lower()

        if choice == 'q':
            break
        elif choice == 'p':
            target = target - jdatetime.timedelta(days=1)
            is_past = (target != today)
        elif choice == 'n':
            target = target + jdatetime.timedelta(days=1)
            is_past = (target != today)

def _show_day_body(target, is_past):
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
