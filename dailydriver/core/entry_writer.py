# dailydriver/core/entry_writer.py
import time
from datetime import datetime
from dailydriver.core.keyword_learner import learn_keywords
# To keep it clean, we'll do a late import inside the function.

def _save_entry(conn, cmd, started_at, duration, selected_paths):
    cur = conn.cursor()
    now_ts = int(time.time())

    cur.execute(
        "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
        (now_ts, started_at, duration, cmd)
    )
    entry_id = cur.lastrowid
    cur.execute("INSERT INTO entries_fts(rowid, description) VALUES (?, ?)", (entry_id, cmd))

    for path in selected_paths:
        cur.execute("SELECT id FROM categories WHERE path=?", (path,))
        row = cur.fetchone()
        if row:
            cur.execute("INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)",
                        (entry_id, row['id']))

    learn_keywords(cmd, selected_paths, conn=conn)

    result = ""
    if selected_paths:
        result += "Logged:\n"
        for p in selected_paths:
            result += f"  {p}\n"
    if started_at is not None:
        start_dt = datetime.fromtimestamp(started_at)
        result += f"Time:   {start_dt.strftime('%H:%M')}\n"
    if duration is not None and duration > 0:
        h = duration // 60
        m = duration % 60
        result += f"Duration: {h}h {m}m\n" if h else f"Duration: {m}m\n"
    return result.strip()

def inject_great_categories(selected_paths: list):
    """If a great event is active, append its categories to selected_paths (no duplicates)."""
    from dailydriver.core.logger import get_active_great_event   # late import to avoid circular
    active = get_active_great_event()
    if active:
        _, ge_cats = active
        for cat in ge_cats:
            if cat not in selected_paths:
                selected_paths.append(cat)
