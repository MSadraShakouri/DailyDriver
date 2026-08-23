"""Persistence helpers for journal entries."""

from __future__ import annotations

import time
from datetime import datetime

from dailydriver.core.state import get_active_great_event

from .keywords import learn_keywords


def save_entry(conn, cmd: str, started_at: int | None, duration: int | None, selected_paths: list[str]) -> str:
    """Insert a journal entry and all category associations."""
    cur = conn.cursor()
    now_ts = int(time.time())
    cur.execute(
        "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
        (now_ts, started_at, duration, cmd),
    )
    entry_id = cur.lastrowid
    cur.execute("INSERT INTO entries_fts(rowid, description) VALUES (?, ?)", (entry_id, cmd))

    for path in selected_paths:
        row = cur.execute("SELECT id FROM categories WHERE path=?", (path,)).fetchone()
        if row:
            cur.execute(
                "INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)",
                (entry_id, row["id"]),
            )

    learn_keywords(cmd, selected_paths, conn=conn)

    result = ""
    if selected_paths:
        result += "Logged:\n"
        for path in selected_paths:
            result += f"  {path}\n"
    if started_at is not None:
        result += f"Time:   {datetime.fromtimestamp(started_at).strftime('%H:%M')}\n"
    if duration is not None and duration > 0:
        hours, minutes = divmod(duration, 60)
        result += f"Duration: {hours}h {minutes}m\n" if hours else f"Duration: {minutes}m\n"
    return result.strip()



def inject_great_categories(selected_paths: list[str]) -> None:
    """Append the active great event's categories without duplicating paths."""
    active = get_active_great_event()
    if active is None:
        return
    _, categories = active
    for category in categories:
        if category not in selected_paths:
            selected_paths.append(category)
