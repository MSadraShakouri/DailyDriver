"""Quick command handlers are tested at their public string boundary."""

from unittest.mock import patch

import pytest

from dailydriver.features.targets import commands, entries, history, router


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ("", "Usage: log <name> <amount>"),
        ("Salavat many", "Amount must be a number."),
        ("Salavat 0", "Amount must be positive."),
    ],
)
def test_log_command_validation(target, today, arguments, expected):
    target()
    assert commands.handle_log_command(arguments) == expected


def test_log_command_updates_matching_kind(target, today):
    entry = target()
    assert "5/100" in commands.handle_log_command("Salavat 5", kind="nazr")
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 5
    assert "not a habit" in commands.handle_log_command("Salavat 1", kind="habit")


def test_daily_total_logs_only_difference(target, today):
    entry = target(name="Reading", kind="habit", target_total=None)
    commands.handle_log_command("Reading 4", kind="habit")
    assert commands.handle_daily_total("Reading 10", kind="habit") == "Reading: 10/∞"
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 10
    assert commands.handle_daily_total("Reading 10") == "No change. Nothing logged."


def test_daily_total_rejects_lower_value(target, today, ui):
    target(name="Reading", kind="habit", target_total=None)
    commands.handle_log_command("Reading 10")
    assert commands.handle_daily_total("Reading 5") == "Negative amount not logged. Please adjust manually."
    assert any("less than" in line for line in ui.lines)


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ("", "Usage: daily_total <name> <total>"),
        ("Salavat many", "Total must be a number."),
        ("Missing 1", "Entry not found: Missing"),
    ],
)
def test_daily_total_validation(target, today, arguments, expected):
    target()
    assert commands.handle_daily_total(arguments) == expected


def test_counter_total_tracks_external_counter(target, today):
    entry = target()
    assert "30/100" in commands.handle_counter_total("Salavat 30")
    assert history.get_counter_value(entry["id"]) == 30
    assert commands.handle_counter_total("Salavat 30") == "No change. Nothing logged."
    assert "Negative" in commands.handle_counter_total("Salavat 20")


def test_counter_reset_does_not_remove_logged_progress(target, today):
    entry = target()
    commands.handle_counter_total("Salavat 30")
    assert commands.handle_counter_reset("Salavat") == "Counter reset to 0 for Salavat"
    assert history.get_counter_value(entry["id"]) == 0
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 30


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ("", "Usage: counter_total <name> <value>"),
        ("Salavat no", "Value must be a number."),
        ("Missing 1", "Entry not found: Missing"),
    ],
)
def test_counter_total_validation(target, today, arguments, expected):
    target()
    assert commands.handle_counter_total(arguments) == expected


def test_router_dispatches_subcommands(target, today):
    target()
    assert "1/100" in router.dispatch("nazr log Salavat 1", kind="nazr")
    assert "Unknown sub-command" in router.dispatch("nazr unknown", kind="nazr")


def test_bare_router_command_opens_filtered_manager():
    with patch("dailydriver.features.targets.manager.show_manager") as show:
        assert router.dispatch("habit", kind="habit") is None
    show.assert_called_once_with(kind="habit")


def test_target_commands_honor_no_last_flag(target, today):
    from dailydriver.core.state import get_last_action_time

    entry = target()
    # By default, target logging updates last_action
    assert get_last_action_time() is None
    commands.handle_log_command("Salavat 5")
    first_ts = get_last_action_time()
    assert first_ts is not None

    # With -n, last_action remains unchanged
    commands.handle_log_command("Salavat 5 -n")
    assert get_last_action_time() == first_ts
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 10

    # With --no-last, last_action remains unchanged
    commands.handle_log_command("Salavat 5 --no-last")
    assert get_last_action_time() == first_ts
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 15

    # -n placed before amount
    commands.handle_log_command("Salavat -n 5")
    assert get_last_action_time() == first_ts
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 20

    # daily_total with -n
    commands.handle_daily_total("Salavat 25 -n")
    assert get_last_action_time() == first_ts
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 25

    # counter_total with --no-last (diff from 0 to 30 adds 30)
    commands.handle_counter_total("Salavat 30 --no-last")
    assert get_last_action_time() == first_ts
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 55
    assert history.get_counter_value(entry["id"]) == 30
