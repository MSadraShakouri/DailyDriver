from unittest.mock import patch

import pytest

from dailydriver.features.qada import commands, entries


def test_bare_command_opens_manager():
    with patch("dailydriver.features.qada.manager.show_qada_manager") as manager:
        assert commands.qada_command("qada") is None
    manager.assert_called_once_with()


def test_unknown_subcommand_is_reported():
    assert commands.qada_command("qada unknown") == "Unknown qada sub-command: unknown"


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ("", "Usage: qada log <slot|id> [amount]"),
        ("missing", "No qada entry found for 'missing'."),
    ],
)
def test_parse_log_validation(db_path, arguments, expected):
    assert commands._parse_log(arguments) == expected


def test_parse_log_resolves_slot_and_amount(qada_entry):
    entry = qada_entry(target_total=5)
    assert "3/5" in commands._parse_log("fajr 3")
    assert entries.get_entry(entry["id"])["logged_total"] == 3


@pytest.mark.parametrize("response", ["", "maybe", "yes please"])
def test_parse_fasting_rejects_invalid_response(db_path, response):
    assert commands._parse_fasting(response) == "Usage: qada fasting yes | qada fasting no"


def test_parse_fasting_requires_entry(db_path):
    assert commands._parse_fasting("yes") == "No fasting entry found. Add one first."


def test_parse_fasting_yes_logs_and_no_pauses(qada_entry):
    fasting = qada_entry(name="Fasting", kind="fasting", target_total=2)
    assert "1/2" in commands._parse_fasting("yes")
    assert "Paused Fasting" in commands._parse_fasting("no")
    assert entries.get_entry(fasting["id"])["paused_until"] is not None
