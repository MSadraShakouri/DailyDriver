# dailydriver/cli/last_view.py
"""Quick view: show the last 5 journal entries without the header."""
import jdatetime
from dailydriver.core.database import get_connection_cm
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
        date_str = jdt.strftime('%Y-%m-%d %H:%M')
        cat_str = row['categories'] or '(no category)'
        desc = (row['description'] or '')[:60].replace('\n', ' ')
        current_ui.print_line(f"[{row['id']}] {date_str}  {cat_str}")
        current_ui.print_line(f"    {desc}")
