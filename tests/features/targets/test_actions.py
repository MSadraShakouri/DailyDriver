"""Manager actions parse UI commands and delegate domain work."""

from unittest.mock import patch

import pytest

from dailydriver.features.targets import actions, entries


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("l", "Usage"),
        ("l no 1", "ID must"),
        ("l 1 no", "Amount must"),
        ("l 1 0", "positive"),
        ("l 404 1", "not found"),
    ],
)
def test_log_action_validation(db_path, ui, command, message):
    actions.log_progress(command)
    assert any(message in line for line in ui.lines)


def test_log_action_updates_entry(target, today, ui):
    entry = target()
    actions.log_progress(f"l {entry['id']} 5", kind="nazr")
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 5
    assert any("5/100" in line for line in ui.lines)


def test_log_action_enforces_manager_kind(target, today, ui):
    entry = target(kind="nazr")
    actions.log_progress(f"l {entry['id']} 1", kind="habit")
    assert any("not a habit" in line for line in ui.lines)


@pytest.mark.parametrize(
    ("command", "message"),
    [
        ("p", "Usage"),
        ("p no", "ID must"),
        ("p 1 no", "Days must"),
        ("p 1 0", "positive"),
    ],
)
def test_pause_action_validation(db_path, ui, command, message):
    actions.toggle_pause(command)
    assert any(message in line for line in ui.lines)


def test_pause_action_updates_entry(target, today, ui):
    entry = target()
    actions.toggle_pause(f"p {entry['id']} 2")
    assert entries.get_entry_by_id(entry["id"])["paused_until"] == "1405-06-03"


def test_total_actions_pass_handler_arguments(target, today, ui):
    entry = target()
    with (
        patch("dailydriver.features.targets.actions.commands.handle_daily_total", return_value="daily") as daily,
        patch("dailydriver.features.targets.actions.commands.handle_counter_total", return_value="counter") as counter,
        patch("dailydriver.features.targets.actions.commands.handle_counter_reset", return_value="reset") as reset,
    ):
        actions.set_daily_total(f"dt {entry['id']} 25", kind="nazr")
        actions.set_counter_total(f"ct {entry['id']} 50", kind="nazr")
        actions.reset_counter(f"cr {entry['id']}", kind="nazr")
    daily.assert_called_once_with("Salavat 25", "nazr")
    counter.assert_called_once_with("Salavat 50", "nazr")
    reset.assert_called_once_with("Salavat", "nazr")
    assert ui.lines[-3:] == ["daily", "counter", "reset"]
