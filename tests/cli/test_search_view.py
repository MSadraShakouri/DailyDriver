"""Tests for token-based, match-count-grouped search."""

from __future__ import annotations

import time

from dailydriver.cli.search_view import _group_header, _query_terms, search
from dailydriver.core.database import get_connection_cm
from dailydriver.display.display_utils import strip_ansi

REVERSE = "\033[7m"


def _insert_entry(conn, description, category=None, created_at=None, started_at=None, duration=None):
    created_at = created_at or int(time.time())
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


def test_query_terms_reports_ignored_words():
    display, stemmed, ignored = _query_terms("i met bob at 5")
    assert display == ["met", "bob"]
    assert len(stemmed) == 2
    assert ignored == ["i", "at"]


def test_query_terms_dedupes_by_stem():
    display, stemmed, ignored = _query_terms("meeting meetings")
    assert len(stemmed) == 1


def test_group_header_wording():
    assert strip_ansi(_group_header(3, 3, 12)) == "── All 3 terms (12 entries) ──"
    assert strip_ansi(_group_header(2, 3, 1)) == "── 2 of 3 terms (1 entry) ──"
    assert strip_ansi(_group_header(1, 1, 4)) == "── 1 term (4 entries) ──"
    assert strip_ansi(_group_header(1, 1, 15, cont=True)) == "── 1 term (15 entries, cont.) ──"


def test_group_header_is_bold_colored():
    header = _group_header(3, 3, 12)
    assert header.startswith("\033[1;36m")
    assert header.endswith("\033[0m")


def test_search_usage_and_no_terms(db_path, ui):
    assert search("search") is None
    assert "Usage" in ui.lines[-1]
    assert search("search a an") is None
    assert "No valid search terms" in ui.lines[-1]


def test_search_groups_by_match_count(db_path, ui):
    now = int(time.time())
    with get_connection_cm() as conn:
        _insert_entry(conn, "python project meeting", created_at=now - 10)
        _insert_entry(conn, "python project notes", created_at=now - 20)
        _insert_entry(conn, "grocery meeting", created_at=now - 30)
        _insert_entry(conn, "nothing relevant", created_at=now - 40)
        conn.commit()

    ui.queue("q")
    search("search python project meeting")
    output = strip_ansi("\n".join(ui.lines))

    assert "── All 3 terms (1 entry) ──" in output
    assert "── 2 of 3 terms (1 entry) ──" in output
    assert "── 1 of 3 terms (1 entry) ──" in output
    assert "nothing relevant" not in output
    # Best group first.
    assert output.index("All 3 terms") < output.index("2 of 3 terms") < output.index("1 of 3 terms")
    assert output.index("python project meeting") < output.index("python project notes")
    # No relevance scores anywhere.
    assert "FTS" not in output
    assert "final" not in output


def test_search_word_boundary_matching(db_path, ui):
    """'art' must not match 'start' — whole-word stems only."""
    now = int(time.time())
    with get_connection_cm() as conn:
        _insert_entry(conn, "start the engine", created_at=now - 10)
        _insert_entry(conn, "made some art today", created_at=now - 20)
        conn.commit()

    ui.queue("q")
    search("search art")
    output = strip_ansi("\n".join(ui.lines))
    assert "made some art today" in output
    assert "start the engine" not in output


def test_search_stem_matching(db_path, ui):
    """'meetings' finds 'meeting' via shared stems."""
    with get_connection_cm() as conn:
        _insert_entry(conn, "weekly meeting with the team")
        conn.commit()

    ui.queue("q")
    search("search meetings")
    assert any("weekly meeting" in strip_ansi(line) for line in ui.lines)


def test_search_matches_categories_and_highlights(db_path, ui):
    with get_connection_cm() as conn:
        _insert_entry(conn, "long session", category="journal/programming")
        conn.commit()

    ui.queue("q")
    search("search programming")
    raw = "\n".join(ui.lines)
    assert "long session" in strip_ansi(raw)
    # The category word that matched is highlighted.
    assert f"{REVERSE}programming" in raw


def test_search_newest_first_within_group_by_start_time(db_path, ui):
    now = int(time.time())
    with get_connection_cm() as conn:
        # Older start time but newer log time: start time wins.
        _insert_entry(conn, "alpha report", created_at=now, started_at=now - 7200)
        _insert_entry(conn, "beta report", created_at=now - 3600)
        conn.commit()

    ui.queue("q")
    search("search report")
    output = strip_ansi("\n".join(ui.lines))
    assert output.index("beta report") < output.index("alpha report")


def test_search_ignored_words_shown(db_path, ui):
    with get_connection_cm() as conn:
        _insert_entry(conn, "met bob downtown")
        conn.commit()

    ui.queue("q")
    search("search i met bob at 5")
    header = next(line for line in ui.lines if line.startswith("🔍"))
    assert "(ignored: i, at)" in header


def test_search_pagination_repeats_group_header(db_path, ui):
    now = int(time.time())
    with get_connection_cm() as conn:
        for i in range(15):
            _insert_entry(conn, f"gym session number{i}", created_at=now - i * 60)
        conn.commit()

    ui.queue("n", "q")
    search("search gym")
    output = strip_ansi("\n".join(ui.lines))
    assert "── 1 term (15 entries) ──" in output
    # Page 2 starts mid-group and repeats the header as a continuation.
    assert "── 1 term (15 entries, cont.) ──" in output
    assert "Showing 11‑15 of 15" in output


def test_search_time_range_display(db_path, ui):
    now = int(time.time())
    with get_connection_cm() as conn:
        _insert_entry(conn, "deep work block", created_at=now, started_at=now - 5400, duration=90)
        conn.commit()

    ui.queue("q")
    search("search deep work")
    output = strip_ansi("\n".join(ui.lines))
    assert "→" in output
    assert "(1h 30m)" in output


def test_search_day_jump_uses_start_time(db_path, ui):
    import jdatetime

    now = int(time.time())
    start = now - 3 * 86400
    with get_connection_cm() as conn:
        entry_id = _insert_entry(conn, "ancient task", created_at=now, started_at=start)
        conn.commit()

    expected_date = jdatetime.datetime.fromtimestamp(start).strftime("%Y-%m-%d")
    ui.queue(f"d {entry_id}", "q")
    search("search ancient")
    assert any(expected_date in line for line in ui.lines)
