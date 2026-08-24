"""Tests for the unified day-view timeline."""

from __future__ import annotations

from datetime import datetime

import jdatetime

from dailydriver.cli.day_view import show_day
from dailydriver.core.database import get_connection_cm
from dailydriver.core.state import (
    DAY_VIEW_MODE_DAY_START,
    DAY_VIEW_MODE_MIDNIGHT,
    get_day_view_mode,
    set_day_view_mode,
)


def _jalali_iso(ts: int) -> str:
    return jdatetime.date.fromgregorian(date=datetime.fromtimestamp(ts).date()).strftime("%Y-%m-%d")


def _noon_today() -> int:
    now = datetime.now()
    return int(datetime(now.year, now.month, now.day, 12, 0).timestamp())


def _seed(conn, ts: int) -> None:
    date = _jalali_iso(ts)
    conn.execute(
        "INSERT OR IGNORE INTO categories (path) VALUES ('journal/work')",
    )
    category_id = conn.execute("SELECT id FROM categories WHERE path='journal/work'").fetchone()[0]
    conn.execute(
        "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
        (ts + 3600, ts + 3600, 30, "wrote the report"),
    )
    entry_id = conn.execute("SELECT id FROM entries ORDER BY id DESC LIMIT 1").fetchone()[0]
    conn.execute("INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)", (entry_id, category_id))
    conn.execute(
        "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time) VALUES (?,?,?,?,?)",
        ("fajr", date, "on_time", ts, ts),
    )
    conn.execute(
        "INSERT INTO sleep_logs (jalali_date, sleep_time, wake_time, duration_minutes) VALUES (?,?,?,?)",
        (date, ts - 3600, ts, 60),
    )
    conn.execute(
        "INSERT INTO nap_logs (jalali_date, start_time, duration_minutes, description) VALUES (?,?,?,?)",
        (date, ts + 7200, 20, "quick nap"),
    )
    conn.commit()


def test_day_view_shows_unified_timeline(db_path, ui):
    noon = _noon_today()
    with get_connection_cm() as conn:
        _seed(conn, noon)

    ui.queue("q")
    show_day("day")
    output = "\n".join(ui.lines)

    assert "📝 Timeline:" in output
    assert "🕌 Fajr" in output
    assert "💤 Sleep" in output
    assert "😴 Nap" in output
    assert "work" in output  # journal categories, journal/ prefix stripped
    assert "journal/work" not in output
    assert "wrote the report" in output
    # Chronological: sleep (11:00) before prayer (12:00) before entry (13:00) before nap (14:00).
    assert output.index("💤 Sleep") < output.index("🕌 Fajr")
    assert output.index("🕌 Fajr") < output.index("wrote the report")
    assert output.index("wrote the report") < output.index("😴 Nap")
    # Journal entry shows a time range.
    assert "→" in output
    assert "(30m)" in output


def test_day_view_empty_day(db_path, ui):
    ui.queue("q")
    show_day("day")
    assert any("Nothing logged." in line for line in ui.lines)


def test_day_view_mode_toggle_persists(db_path, ui):
    assert get_day_view_mode() == DAY_VIEW_MODE_MIDNIGHT
    ui.queue("m", "q")
    show_day("day")
    assert get_day_view_mode() == DAY_VIEW_MODE_DAY_START
    output = "\n".join(ui.lines)
    assert "midnight" in output
    assert "day start" in output

    # Next visit starts in the persisted mode and can toggle back.
    ui.lines.clear()
    ui.queue("m", "q")
    show_day("day")
    assert get_day_view_mode() == DAY_VIEW_MODE_MIDNIGHT


def test_day_view_daystart_mode_claims_early_morning(db_path, ui):
    """In day-start mode, 02:00 activity belongs to the previous day's view."""
    noon = _noon_today()
    two_am_tomorrow = noon + 14 * 3600  # 02:00 next day
    with get_connection_cm() as conn:
        conn.execute(
            "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
            (two_am_tomorrow, two_am_tomorrow, None, "late night note"),
        )
        conn.commit()

    # Midnight mode: not on today's view.
    ui.queue("q")
    show_day("day")
    assert "late night note" not in "\n".join(ui.lines)

    # Day-start mode (default hour 4): included in today's view.
    set_day_view_mode(DAY_VIEW_MODE_DAY_START)
    ui.lines.clear()
    ui.queue("q")
    show_day("day")
    assert "late night note" in "\n".join(ui.lines)
