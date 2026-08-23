from unittest.mock import patch

from dailydriver.features.targets import actions

ENTRY = {"id": 7, "name": "Salavat", "kind": "nazr"}


@patch("dailydriver.features.targets.actions.current_ui")
@patch("dailydriver.features.targets.actions.commands.handle_daily_total", return_value="ok")
@patch("dailydriver.features.targets.actions.entries.get_entry_by_id", return_value=ENTRY)
def test_manager_daily_total_passes_only_handler_arguments(mock_entry, mock_handle, mock_ui):
    actions.set_daily_total("dt 7 25", kind="nazr")
    mock_handle.assert_called_once_with("Salavat 25", "nazr")
    mock_ui.print_line.assert_called_with("ok")


@patch("dailydriver.features.targets.actions.current_ui")
@patch("dailydriver.features.targets.actions.commands.handle_counter_total", return_value="ok")
@patch("dailydriver.features.targets.actions.entries.get_entry_by_id", return_value=ENTRY)
def test_manager_counter_total_passes_only_handler_arguments(mock_entry, mock_handle, mock_ui):
    actions.set_counter_total("ct 7 50", kind="nazr")
    mock_handle.assert_called_once_with("Salavat 50", "nazr")
    mock_ui.print_line.assert_called_with("ok")


@patch("dailydriver.features.targets.actions.current_ui")
@patch("dailydriver.features.targets.actions.commands.handle_counter_reset", return_value="ok")
@patch("dailydriver.features.targets.actions.entries.get_entry_by_id", return_value=ENTRY)
def test_manager_counter_reset_passes_only_entry_name(mock_entry, mock_handle, mock_ui):
    actions.reset_counter("cr 7", kind="nazr")
    mock_handle.assert_called_once_with("Salavat", "nazr")
    mock_ui.print_line.assert_called_with("ok")
