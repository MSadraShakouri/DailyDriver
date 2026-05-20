import os
import re
import shutil
import subprocess
import sys

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.core.logger import log_free_text
from dailydriver.display.display_utils import pline_wrap, wrap_line
from dailydriver.ui.terminal_ui import current_ui


def view_entries(category_filter=None):
    with get_connection_cm() as conn:
        cur = conn.cursor()
        page_size = 10
        offset = 0

        # Base query (without LIMIT, for counting later)
        base_sql = """
            SELECT e.id, e.created_at, e.duration_minutes, e.description,
                   GROUP_CONCAT(c.path, ', ') AS categories
            FROM entries e
            LEFT JOIN entry_categories ec ON e.id = ec.entry_id
            LEFT JOIN categories c ON ec.category_id = c.id
        """
        where_clause = ""
        params = []

        if category_filter:
            where_clause = " WHERE LOWER(c.path) LIKE ?"
            params.append("%" + category_filter.lower() + "%")
            # For count, we need to filter at entry level
            # We'll use a subquery

        query_sql = base_sql + where_clause + """
            GROUP BY e.id
            ORDER BY e.created_at DESC
            LIMIT ? OFFSET ?
        """

        while True:
            cur.execute(query_sql, params + [page_size, offset])
            rows = cur.fetchall()

            if not rows and offset == 0:
                current_ui.print_line("No entries found.")
                return  # connection closed by context manager

            current_ui.clear()
            filter_str = f" [filter: {category_filter}]" if category_filter else ""
            current_ui.print_line(f"─────── Journal Entries{filter_str} ───────")
            for row in rows:
                jdt = jdatetime.datetime.fromtimestamp(row["created_at"])
                # Line 1: ID + date + time
                current_ui.print_line(f"[{row['id']}] {jdt.strftime('%Y-%m-%d %H:%M')}")
                # Categories indented under the date
                cats = row["categories"] or "(no category)"
                cats_indent = " " * len(f"[{row['id']}] ")
                wrap_line(cats_indent, cats, cats_indent)
                # Description
                desc = (row["description"] or "").replace("\n", " ")
                pline_wrap(desc, indent=2, max_lines=2)
                current_ui.print_line()

            current_ui.print_line(
                "\033[1m(n)ext  (p)rev  (q)uit  [id] edit  (d)ay <id>\033[0m"
            )
            current_ui.print_line("\033[1mn/p = next/prev page, 5n = 5 pages\033[0m")
            current_ui.print_line()
            choice = current_ui.prompt("> ").strip().lower()

            if choice == "q":
                break
            elif re.match(r"^\d*[np]$", choice):
                steps = int(choice[:-1]) if choice[:-1] else 1
                if choice[-1] == "n":
                    if len(rows) == page_size:
                        offset += steps * page_size
                    else:
                        current_ui.print_line("No more pages.")
                        current_ui.prompt("Press Enter to continue.")
                else:  # 'p'
                    offset = max(0, offset - steps * page_size)

            elif choice.startswith("d"):
                parts = choice.split(maxsplit=1)
                if len(parts) == 2:
                    eid = parts[1].strip()
                else:
                    eid = current_ui.prompt("Entry ID: ").strip()
                if eid.isdigit():
                    from dailydriver.cli.day_view import show_day

                    with get_connection_cm() as conn2:
                        cur2 = conn2.cursor()
                        cur2.execute(
                            "SELECT created_at FROM entries WHERE id=?", (int(eid),)
                        )
                        row2 = cur2.fetchone()
                        if row2:
                            jd = jdatetime.datetime.fromtimestamp(row2["created_at"])
                            show_day(jd.strftime("%Y-%m-%d"))
                            return
                        else:
                            current_ui.print_line("Entry not found.")
                            current_ui.prompt("Press Enter to continue.")

            elif choice.isdigit():
                entry_id = int(choice)
                result = edit_entry(entry_id)
                if result is not None:
                    log_free_text(result)
                    return  # connection closed by context manager
            else:
                pass


def edit_entry(entry_id):
    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute("SELECT description FROM entries WHERE id=?", (entry_id,))
        row = cur.fetchone()
        if not row:
            current_ui.print_line("Entry not found.")
            return None

        BASE_DIR = os.path.dirname(os.path.realpath(__file__))
        tmp_file = os.path.join(BASE_DIR, ".daily_edit.txt")

        with open(tmp_file, "w") as f:
            f.write(row["description"] or "")

        # Prefer nvim (Termux‑specific path, then global)
        termux_nvim = "/data/data/com.termux/files/usr/bin/nvim"
        if os.path.exists(termux_nvim):
            editor = termux_nvim
        elif shutil.which("nvim"):
            editor = "nvim"
        else:
            editor = "nano"

        subprocess.call(
            [editor, tmp_file],
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

        with open(tmp_file, "r") as f:
            new_desc = f.read().strip()

        if new_desc == (row["description"] or "").strip():
            current_ui.print_line("No changes.")
            return None

        cur.execute("DELETE FROM entries_fts WHERE rowid=?", (entry_id,))
        # Delete child rows first
        cur.execute("DELETE FROM entry_categories WHERE entry_id=?", (entry_id,))
        # Delete the entry itself
        cur.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        conn.commit()
        return new_desc
