"""Interactive target forms, table rendering, and manager routing."""

from unittest.mock import patch

from dailydriver.features.targets import entries, forms, manager, table


def test_add_form_persists_answers(db_path, ui):
    ui.queue("Reading", "100", "d", "10", "")
    forms.add_entry(default_kind="habit")
    entry = entries.get_entry_by_name("Reading")
    assert entry["kind"] == "habit"
    assert entry["target_total"] == 100
    assert entry["interval_type"] == "daily"
    assert entry["target_per_interval"] == 10
    assert any("Added: Reading" in line for line in ui.lines)


def test_add_form_rejects_missing_name(db_path, ui):
    ui.queue("")
    forms.add_entry(default_kind="nazr")
    assert entries.get_all_entries() == []
    assert "Name is required. Cancelled." in ui.lines


def test_edit_form_updates_values(target, ui):
    entry = target()
    ui.queue("Renamed", "200", "w", "3", "20", "")
    forms.edit_entry(f"e {entry['id']}")
    updated = entries.get_entry_by_id(entry["id"])
    assert (updated["name"], updated["target_total"]) == ("Renamed", 200)
    assert (updated["interval_type"], updated["interval_value"]) == ("weekly", 3)
    assert updated["target_per_interval"] == 20


def test_delete_form_honors_confirmation(target, ui):
    entry = target()
    ui.queue("n", "")
    forms.delete_entry(f"d {entry['id']}")
    assert entries.get_entry_by_id(entry["id"]) is not None

    ui.queue("y", "")
    forms.delete_entry(f"d {entry['id']}")
    assert entries.get_entry_by_id(entry["id"]) is None


def test_table_renders_finite_indefinite_complete_and_paused_rows(target, today, ui, monkeypatch):
    finite = target(name="Finite", target_total=100)
    target(name="Habit", kind="habit", target_total=None)
    complete = target(name="Complete", target_total=1)
    entries.record_progress(complete["id"], 1, 1, today.strftime("%Y-%m-%d"), 1)
    paused = target(name="Paused", target_total=10)
    entries.toggle_pause(paused["id"], 2)
    monkeypatch.setattr("dailydriver.features.targets.table.get_width", lambda: 100)

    table.render_entries(entries.get_all_entries())

    output = "\n".join(ui.lines)
    assert all(name in output for name in ("Finite", "Habit", "Complete", "Paused"))
    assert "∞" in output
    assert "\033[32m" in output
    assert "\033[2m" in output


def test_manager_quits_cleanly_with_no_entries(db_path, ui):
    ui.queue("q")
    with (
        patch("dailydriver.features.targets.manager.build_header_data", return_value={}),
        patch("dailydriver.features.targets.manager.print_header"),
    ):
        manager.show_manager(kind="habit")
    assert ui.cleared == 1


def test_manager_routes_selected_action(target, ui):
    entry = target()
    ui.queue(f"l {entry['id']} 2", "q")
    with (
        patch("dailydriver.features.targets.manager.build_header_data", return_value={}),
        patch("dailydriver.features.targets.manager.print_header"),
        patch("dailydriver.features.targets.manager.table.render_entries"),
        patch("dailydriver.features.targets.manager.actions.log_progress") as log,
    ):
        manager.show_manager(kind="nazr")
    log.assert_called_once_with(f"l {entry['id']} 2", "nazr")
