# dailydriver/cli/last_view.py
"""Quick view: show the last 5 journal entries, layout matching view."""
import jdatetime
from dailydriver.core.database import get_connection_cm
from dailydriver.display.display_utils import pline_wrap, wrap_line
from dailydriver.ui.terminal_ui import current_ui


def show_last():
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT e.id, e.created_at, e.description,
                   GROUP_CONCAT(c.path, ', ') AS categories
            FROM entries e
            LEFT JOIN entry_categories ec ON e.id = ec.entry_id
            LEFT JOIN categories c ON ec.category_id = c.id
            GROUP BY e.id
            ORDER BY e.created_at DESC
            LIMIT 5
        """)
        rows = cur.fetchall()

    if not rows:
        current_ui.print_line("No entries yet.")
        return

    current_ui.print_line("─── Last 5 Entries ───")
    for row in rows:
        jdt = jdatetime.datetime.fromtimestamp(row['created_at'])
        # Line 1: ID + date + time
        current_ui.print_line(f"[{row['id']}] {jdt.strftime('%Y-%m-%d %H:%M')}")
        # Categories indented under the date
        cats = row['categories'] or '(no category)'
        cats_indent = ' ' * len(f"[{row['id']}] ")
        wrap_line(cats_indent, cats, cats_indent)
        # Description
        desc = (row['description'] or '').replace('\n', ' ')
        pline_wrap(desc, indent=2, max_lines=2)
        current_ui.print_line()
