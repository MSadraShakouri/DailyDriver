import os
import subprocess
import time
from database import get_connection
from database import commit_and_update
from logger import log_free_text

def view_entries(category_filter=None):
    conn = get_connection()
    cur = conn.cursor()
    page_size = 20
    offset = 0

    # Base query (without LIMIT, for counting later)
    base_sql = '''
        SELECT e.id, e.created_at, e.duration_minutes, e.description,
               GROUP_CONCAT(c.path, ', ') AS categories
        FROM entries e
        LEFT JOIN entry_categories ec ON e.id = ec.entry_id
        LEFT JOIN categories c ON ec.category_id = c.id
    '''
    count_sql = '''
        SELECT COUNT(DISTINCT e.id)
        FROM entries e
        LEFT JOIN entry_categories ec ON e.id = ec.entry_id
        LEFT JOIN categories c ON ec.category_id = c.id
    '''
    where_clause = ''
    params = []

    if category_filter:
        where_clause = " WHERE LOWER(c.path) LIKE ?"
        params.append('%' + category_filter.lower() + '%')
        # For count, we need to filter at entry level
        # We'll use a subquery

    query_sql = base_sql + where_clause + '''
        GROUP BY e.id
        ORDER BY e.created_at DESC
        LIMIT ? OFFSET ?
    '''

    while True:
        cur.execute(query_sql, params + [page_size, offset])
        rows = cur.fetchall()

        if not rows and offset == 0:
            print("No entries found.")
            conn.close()
            return

        os.system('clear')
        filter_str = f" [filter: {category_filter}]" if category_filter else ""
        print(f"─────── Journal Entries{filter_str} ───────")
        for row in rows:
            from datetime import datetime
            dt = datetime.fromtimestamp(row['created_at'])
            cat_str = row['categories'] if row['categories'] else '(no category)'
            desc_snippet = (row['description'] or '')[:50].replace('\n', ' ')
            print(f"[{row['id']}] {dt.strftime('%Y-%m-%d %H:%M')}  {cat_str}")
            print(f"    {desc_snippet}")

        print("\n(n)ext  (p)rev  (q)uit  [id] edit")
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
                conn.close()
                log_free_text(result)
                return
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
    commit_and_update(conn)
    conn.close()

    return new_desc
