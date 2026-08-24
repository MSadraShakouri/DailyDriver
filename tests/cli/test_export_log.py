import time
from datetime import datetime

import jdatetime

from dailydriver.cli.export_log import _parse_duration, export
from dailydriver.core.database import get_connection_cm
from dailydriver.features.qada.entries import add_entry as add_qada
from dailydriver.features.qada.logging import log_prayer_qada
from dailydriver.features.targets.entries import add_entry as add_target
from dailydriver.features.targets.progress import log_progress


def _jalali_iso_from_timestamp(ts: int) -> str:
    return jdatetime.date.fromgregorian(date=datetime.fromtimestamp(ts).date()).strftime("%Y-%m-%d")


def test_duration_parser_supports_all():
    assert _parse_duration("all") == 0
    assert _parse_duration("7d") == 7
    assert _parse_duration("bad") is None


def test_export_validates_arguments(db_path, ui):
    assert export("export") is None
    assert "Usage" in ui.lines[-1]
    assert export("export forever") is None
    assert "Invalid duration" in ui.lines[-1]


def test_export_writes_unified_markdown_timeline(db_path, tmp_path, monkeypatch):
    now = int(time.time())
    prayer_qada_ts = now + 20
    prayer_qada_date = _jalali_iso_from_timestamp(prayer_qada_ts)

    with get_connection_cm() as conn:
        conn.execute("INSERT OR IGNORE INTO categories (path) VALUES ('journal/work')")
        category_id = conn.execute("SELECT id FROM categories WHERE path='journal/work'").fetchone()[0]
        conn.execute(
            "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
            (now + 60, now + 60, 30, "journal details"),
        )
        entry_id = conn.execute("SELECT id FROM entries ORDER BY id DESC LIMIT 1").fetchone()[0]
        conn.execute("INSERT INTO entries_fts(rowid, description) VALUES (?, ?)", (entry_id, "journal details"))
        conn.execute("INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)", (entry_id, category_id))
        conn.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time) VALUES (?,?,?,?,?)",
            ("fajr", prayer_qada_date, "qada", prayer_qada_ts, prayer_qada_ts),
        )
        conn.execute(
            "INSERT INTO sleep_logs (jalali_date, sleep_time, wake_time, duration_minutes) VALUES (?,?,?,?)",
            (_jalali_iso_from_timestamp(now), now, now + 8 * 3600, 8 * 60),
        )
        conn.commit()

    add_target("habit", "pushups")
    log_progress("pushups", 3)
    qada_id = add_qada("Fajr", "prayer", slot="fajr", target_total=10)
    log_prayer_qada(qada_id, 2, now=now + 40)

    monkeypatch.chdir(tmp_path)
    assert export("export all --md") == "Exported to export_all.md (format: MD)"
    content = (tmp_path / "export_all.md").read_text()
    expected_prayer_qada_date = jdatetime.date(*map(int, prayer_qada_date.split("-"))).strftime("%d %B %Y")

    assert "# Export (all time)" in content
    assert "**💤 Sleep**" in content
    assert "**🕌 Fajr**" in content
    assert f"> 🕯️ Qada for {expected_prayer_qada_date}" in content
    assert "**📿 Qada: Fajr**" in content
    assert "**🎯 Habit: pushups**" in content
    assert "**work**" in content
    assert "journal/work" not in content
    assert "> journal details" in content
    assert (
        content.index("**💤 Sleep**")
        < content.index("**🕌 Fajr**")
        < content.index("**📿 Qada: Fajr**")
        < content.index("**work**")
    )


def test_export_text_uses_unified_day_blocks(db_path, tmp_path, monkeypatch):
    now = int(time.time())
    with get_connection_cm() as conn:
        conn.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time) VALUES (?,?,?,?,?)",
            ("fajr", _jalali_iso_from_timestamp(now), "on_time", now, now),
        )
        conn.commit()
    monkeypatch.chdir(tmp_path)
    assert export("export all --txt") == "Exported to export_all.txt (format: TXT)"
    content = (tmp_path / "export_all.txt").read_text()
    assert "══════ Export (all time) ══════" in content
    assert "── " in content
    assert "🕌 Fajr" in content


def test_export_items_hooks_respect_end_bound(db_path):
    """Every export_items implementation honors the inclusive upper bound."""
    from dailydriver.core.journal import get_export_items
    from dailydriver.features.prayer.export import export_items as prayer_items
    from dailydriver.features.qada.export import export_items as qada_items
    from dailydriver.features.sleep.export import export_items as sleep_items
    from dailydriver.features.targets.export import export_items as target_items

    early, late = 1_000_000, 2_000_000
    with get_connection_cm() as conn:
        for ts in (early, late):
            date = _jalali_iso_from_timestamp(ts)
            conn.execute(
                "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
                (ts, ts, 10, f"entry-{ts}"),
            )
            conn.execute(
                "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time) VALUES (?,?,?,?,?)",
                ("fajr", date, "on_time", ts, ts),
            )
            conn.execute(
                "INSERT INTO sleep_logs (jalali_date, sleep_time, wake_time, duration_minutes) VALUES (?,?,?,?)",
                (date, ts, ts + 3600, 60),
            )
            conn.execute(
                "INSERT INTO nap_logs (jalali_date, start_time, duration_minutes, description) VALUES (?,?,?,?)",
                (date, ts, 20, "nap"),
            )
        conn.commit()

    add_target("habit", "walk")
    log_progress("walk", 1)
    qada_id = add_qada("Fajr", "prayer", slot="fajr", target_total=5)
    log_prayer_qada(qada_id, 1, now=late)
    with get_connection_cm() as conn:
        conn.execute("UPDATE target_logs SET logged_at=?", (late,))
        conn.execute("UPDATE qada_logs SET logged_at=?", (late,))
        conn.commit()

    with get_connection_cm(auto=False) as conn:
        # end=None keeps everything at/after start.
        assert len(get_export_items(conn, 0)) == 2
        # Inclusive upper bound keeps `early`, drops `late`.
        assert [i["timestamp"] for i in get_export_items(conn, 0, early)] == [early]
        assert [i["timestamp"] for i in prayer_items(conn, 0, early)] == [early]
        sleep_only = sleep_items(conn, 0, early)
        assert len(sleep_only) == 2  # one sleep + one nap
        assert all(i["timestamp"] == early for i in sleep_only)
        assert target_items(conn, 0, early) == []
        assert qada_items(conn, 0, early) == []
        assert [i["timestamp"] for i in target_items(conn, 0, late)] == [late]
        assert [i["timestamp"] for i in qada_items(conn, 0, late)] == [late]
        # Inclusive both ends.
        assert [i["timestamp"] for i in get_export_items(conn, late, late)] == [late]


def test_export_date_headers_include_abbreviated_weekday(db_path, tmp_path, monkeypatch):
    from datetime import datetime as _dt

    now = int(time.time())
    with get_connection_cm() as conn:
        conn.execute(
            "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
            (now, now, None, "weekday check"),
        )
        conn.commit()

    weekday = _dt.fromtimestamp(now).strftime("%a")
    jalali = jdatetime.datetime.fromtimestamp(now).strftime("%d %B %Y")

    monkeypatch.chdir(tmp_path)
    export("export all --md")
    md = (tmp_path / "export_all.md").read_text()
    assert f"### {weekday}, {jalali}" in md

    export("export all --txt")
    txt = (tmp_path / "export_all.txt").read_text()
    assert f"── {weekday}, {jalali} ──" in txt
