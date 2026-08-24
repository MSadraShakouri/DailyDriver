"""Tests for the entry browser (`view`)."""

from __future__ import annotations

import time

import jdatetime

from dailydriver.cli.entry_viewer import entry_time_display, view_entries
from dailydriver.core.database import get_connection_cm


def _insert_entry(conn, created_at, started_at=None, duration=None, description="", category=None):
    conn.execute(
        "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
        (created_at, started_at, duration, description),
    )
    entry_id = conn.execute("SELECT id FROM entries ORDER BY id DESC LIMIT 1").fetchone()[0]
    if category:
        conn.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (category,))
        category_id = conn.execute("SELECT id FROM categories WHERE path=?", (category,)).fetchone()[0]
        conn.execute("INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)", (entry_id, category_id))
    return entry_id


def test_entry_time_display_range_and_plain():
    ts = 1_700_000_000
    jdt = jdatetime.datetime.fromtimestamp(ts)
    plain = entry_time_display(None, ts, None)
    assert plain == jdt.strftime("%Y-%m-%d %H:%M")
    ranged = entry_time_display(ts, ts - 999, 90)
    assert ranged.startswith(jdt.strftime("%Y-%m-%d %H:%M"))
    assert "→" in ranged
    assert "(1h 30m)" in ranged


def test_view_shows_time_range_when_duration_present(db_path, ui):
    now = int(time.time())
    with get_connection_cm() as conn:
        _insert_entry(conn, now, started_at=now - 1800, duration=30, description="ranged", category="journal/work")
        _insert_entry(conn, now - 60, description="plain one")
        conn.commit()

    ui.queue("q")
    view_entries()
    output = "\n".join(ui.lines)
    assert "→" in output
    assert "(30m)" in output
    assert "ranged" in output
    assert "plain one" in output


def test_view_sorts_by_start_time_desc(db_path, ui):
    now = int(time.time())
    with get_connection_cm() as conn:
        # Logged later but started earlier: must sort by the start time.
        _insert_entry(conn, now, started_at=now - 7200, description="started earlier")
        _insert_entry(conn, now - 3600, description="logged earlier")
        conn.commit()

    ui.queue("q")
    view_entries()
    output = "\n".join(ui.lines)
    assert output.index("logged earlier") < output.index("started earlier")


def test_view_day_jump_uses_start_time(db_path, ui):
    now = int(time.time())
    start = now - 3 * 86400  # started three days ago, logged now
    with get_connection_cm() as conn:
        entry_id = _insert_entry(conn, now, started_at=start, duration=15, description="old start")
        conn.commit()

    expected_date = jdatetime.datetime.fromtimestamp(start).strftime("%Y-%m-%d")
    ui.queue(f"d {entry_id}", "q")
    view_entries()
    output = "\n".join(ui.lines)
    # The day view header renders the target Jalali date.
    assert expected_date in output or any(expected_date in line for line in ui.lines)
