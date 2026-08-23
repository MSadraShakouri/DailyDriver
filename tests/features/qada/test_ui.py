from unittest.mock import patch

import jdatetime

from dailydriver.features.qada import editor, entries, manager, overview, table


def _configured_rows():
    rows = overview.get_all_entries_with_progress()
    for row in rows:
        entries.edit_entry(row["id"], target_total=10)
    return overview.get_all_entries_with_progress()


def test_editor_sets_target(db_path, ui):
    row = overview.get_all_entries_with_progress()[0]
    ui.queue("10", "1", "")
    editor.edit_entry("e 1")
    assert entries.get_entry(row["id"])["target_total"] == 10
    assert any("Target updated" in line for line in ui.lines)


def test_editor_validates_index(db_path, ui):
    editor.edit_entry("e invalid")
    assert "Invalid number." in ui.lines
    ui.lines.clear()
    editor.edit_entry("e 99")
    assert any("not found" in line for line in ui.lines)


def test_table_renders_progress_states(db_path, ui, monkeypatch):
    rows = _configured_rows()
    paused_until = (jdatetime.date.today() + jdatetime.timedelta(days=1)).strftime("%Y-%m-%d")
    entries.edit_entry(rows[1]["id"], paused_until=paused_until)
    entries.edit_entry(rows[2]["id"], target_total=0)
    monkeypatch.setattr("dailydriver.features.qada.table.get_width", lambda: 100)
    table.render_entries(overview.get_all_entries_with_progress())
    output = "\n".join(ui.lines)
    assert all(name in output for name in ("Fajr", "Dhuhr/Asr", "Maghrib/Isha", "Fasting"))
    assert "\033[2m" in output
    assert "\033[32m" in output


def test_manager_log_and_pause_actions(db_path, ui):
    rows = _configured_rows()
    ui.queue("2", "")
    manager._log_entry("l 1")
    assert entries.get_entry(rows[0]["id"])["logged_total"] == 2

    ui.queue("2", "")
    manager._pause_entry("p 1")
    assert entries.get_entry(rows[0]["id"])["paused_until"] is not None


def test_manager_quits_cleanly(db_path, ui):
    ui.queue("q")
    with (
        patch("dailydriver.features.qada.manager.build_header_data", return_value={}),
        patch("dailydriver.features.qada.manager.print_header"),
        patch("dailydriver.features.qada.manager.render_entries"),
    ):
        manager.show_qada_manager()
    assert ui.cleared == 1


def test_manager_routes_edit(db_path, ui):
    ui.queue("e 1", "q")
    with (
        patch("dailydriver.features.qada.manager.build_header_data", return_value={}),
        patch("dailydriver.features.qada.manager.print_header"),
        patch("dailydriver.features.qada.manager.render_entries"),
        patch("dailydriver.features.qada.manager.edit_entry") as edit,
    ):
        manager.show_qada_manager()
    edit.assert_called_once_with("e 1")
