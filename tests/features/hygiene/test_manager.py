from unittest.mock import patch

from dailydriver.features.hygiene.manager import manage_hygiene


def _manager_patches():
    return (
        patch("dailydriver.features.hygiene.manager.build_header_data", return_value={}),
        patch("dailydriver.features.hygiene.manager.print_header"),
    )


def test_empty_manager_quits(db_path, ui):
    ui.queue("q")
    with _manager_patches()[0], _manager_patches()[1]:
        manage_hygiene()
    assert "  No hygiene items configured." in ui.lines


def test_manager_renders_configured_item(db_connection, ui, monkeypatch):
    db_connection.execute("""INSERT INTO hygiene_config
           (item, desired_interval_days, early_warning_enabled, show_due_today)
           VALUES ('shower', 3, 1, 1)""")
    db_connection.commit()
    ui.queue("q")
    monkeypatch.setattr("dailydriver.features.hygiene.manager.get_width", lambda: 80)
    with (
        patch("dailydriver.features.hygiene.manager.build_header_data", return_value={}),
        patch("dailydriver.features.hygiene.manager.print_header"),
    ):
        manage_hygiene()
    assert "shower" in "\n".join(ui.lines)


def test_manager_routes_add_action(db_path, ui):
    ui.queue("a", "q")
    with (
        patch("dailydriver.features.hygiene.manager.build_header_data", return_value={}),
        patch("dailydriver.features.hygiene.manager.print_header"),
        patch("dailydriver.features.hygiene.manager.add_hygiene_item") as add,
    ):
        manage_hygiene()
    add.assert_called_once()
