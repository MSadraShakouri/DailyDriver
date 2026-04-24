import os
import subprocess
import time
from database import get_connection
from logger import log_free_text

def view_entries():
    conn = get_connection()
    cur = conn.cursor()
    page_size = 20
    offset = 0

    while True:
        cur.execute('''
            SELECT e.id, e.created_at, e.duration_minutes, e.description,
                   GROUP_CONCAT(c.path, ', ') AS categories
            FROM entries e
            LEFT JOIN entry_categories ec ON e.id = ec.entry_id
            LEFT JOIN categories c ON ec.category_id = c.id
            GROUP BY e.id
            ORDER BY e.created_at DESC
            LIMIT ? OFFSET ?
        ''', (page_size, offset))
        rows = cur.fetchall()

        if not rows and offset == 0:
            print("No entries yet.")
            conn.close()
            return

        os.system('clear')
        print("─────── Journal Entries ───────")
        for row in rows:
            from datetime import datetime
            dt = datetime.fromtimestamp(row['created_at'])
            cat_str = row['categories'] if row['categories'] else '(no category)'
            desc_snippet = (row['description'] or '')[:50].replace('\n', ' ')
            print(f"[{row['id']}] {dt.strftime('%Y-%m-%d %H:%M')}  {cat_str}")
            print(f"    {desc_snippet}")

        print("\n(n)ext page  (p)rev page  [id] edit  (q)uit view")
        choice = input("> ").strip().lower()

        if choice == 'q':
            break
        elif choice == 'n':
            if len(rows) == page_size:
                offset += page_size
            else:
                print("No more pages.")
                input()
        elif choice == 'p':
            offset = max(0, offset - page_size)
        elif choice.isdigit():
            entry_id = int(choice)
            result = edit_entry(entry_id)
            if result is not None:
                # The entry was edited – re-logged with full prompts
                conn.close()
                log_free_text(result)      # will ask for category/flags
                return                     # exit view to REPL
        else:
            pass

    conn.close()

def edit_entry(entry_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT description FROM entries WHERE id=?", (entry_id,))
    row = cur.fetchone()
    if not row:
        print("Entry not found.")
        conn.close()
        return None

    tmp_file = os.path.expanduser('~/.daily_edit.txt')
    with open(tmp_file, 'w') as f:
        f.write(row['description'] or '')

    subprocess.call(['nano', tmp_file])

    with open(tmp_file, 'r') as f:
        new_desc = f.read().strip()

    if new_desc == (row['description'] or '').strip():
        print("No changes.")
        conn.close()
        return None

    # Delete child rows first (foreign keys)
    cur.execute("DELETE FROM entry_categories WHERE entry_id=?", (entry_id,))
    cur.execute("DELETE FROM entry_flags WHERE entry_id=?", (entry_id,))
    # Now delete the entry itself
    cur.execute("DELETE FROM entries WHERE id=?", (entry_id,))
    conn.commit()
    conn.close()

    return new_desc
