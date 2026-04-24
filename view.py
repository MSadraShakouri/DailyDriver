import os
import time
import subprocess
from database import get_connection

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
            edit_entry(entry_id)
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
        return

    # Write current description to a temp file
    tmp_file = os.path.expanduser('~/.daily_edit.txt')
    with open(tmp_file, 'w') as f:
        f.write(row['description'] or '')

    # Open nano
    subprocess.call(['nano', tmp_file])

    # Read back
    with open(tmp_file, 'r') as f:
        new_desc = f.read().strip()

    if new_desc == (row['description'] or '').strip():
        print("No changes.")
        return

    # Re‑parse the new text through the logger (but we need the parser functions)
    # For now, we simply update the description and reset created_at
    import time
    cur.execute("UPDATE entries SET description=?, created_at=? WHERE id=?",
                (new_desc, int(time.time()), entry_id))
    conn.commit()
    print("Entry updated. (categories/flags not re‑parsed from edit – simple update for now)")
