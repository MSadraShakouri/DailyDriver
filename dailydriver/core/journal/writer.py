"""Persistence helpers for journal entries."""

from __future__ import annotations

import time

from dailydriver.core.export_utils import format_time_range
from dailydriver.core.state import get_active_injected_categories

from .keywords import learn_keywords


def save_entry(conn, cmd: str, started_at: int | None, duration: int | None, selected_paths: list[str]) -> str:
    """Insert a journal entry and all category associations."""
    selected_paths = list(dict.fromkeys(selected_paths))
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
        if not row:
            # Defend against stale active-event metadata as well as future
            # callers that provide a fresh category path directly.
            cur.execute("INSERT INTO categories (path) VALUES (?)", (path,))
            category_id = cur.lastrowid
        else:
            category_id = row["id"]
        cur.execute(
            "INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)",
            (entry_id, category_id),
        )

    learn_keywords(cmd, selected_paths, conn=conn)

    result = ""
    if selected_paths:
        result += "Logged:\n"
        for path in selected_paths:
            result += f"  {path}\n"
    if started_at is not None:
        result += f"Time:   {format_time_range(started_at, duration)}\n"
    return result.strip()


def inject_great_categories(selected_paths: list[str]) -> None:
    """Append categories from all active injectors without duplicates.

    The historic function name remains for compatibility with the old great
    event command; numbered states now contribute to the same injected set.
    """
    for category in get_active_injected_categories():
        if category not in selected_paths:
            selected_paths.append(category)
