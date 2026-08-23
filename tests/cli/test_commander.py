from unittest.mock import Mock, patch

import pytest

from dailydriver.cli import commander


@pytest.mark.parametrize(
    ("lines", "target", "argument"),
    [
        (["ln replied", "details"], "log_chain_now", "ln replied\ndetails"),
        (["ee task", "details"], "log_event_end", "ee task\ndetails"),
        (["ege finished", "details"], "end_great_event_cmd", "ege finished\ndetails"),
        (["ege"], "end_great_event_cmd", "ege "),
    ],
)
def test_multiline_event_commands_use_real_router(lines, target, argument):
    with patch(f"dailydriver.cli.commands.events.{target}") as handler:
        commander._submit_multiline(lines)
    handler.assert_called_once_with(argument)


def test_plain_multiline_is_logged_as_journal_entry(monkeypatch):
    log = Mock()
    monkeypatch.setattr(commander, "log_free_text", log)
    commander._submit_multiline(["first", "second"])
    log.assert_called_once_with("first\nsecond")


def test_single_command_routes_handler_and_displays_result(ui, monkeypatch):
    handler = Mock(return_value="done")
    monkeypatch.setattr(commander, "make_dispatch", lambda: {"test": handler})
    monkeypatch.setattr(commander, "build_header_data", lambda: {})
    monkeypatch.setattr(commander, "print_header", lambda *args, **kwargs: None)
    shown = []
    monkeypatch.setattr(commander, "_show_result", shown.append)
    commander.run_single_command("test value")
    handler.assert_called_once_with("test value")
    assert shown == ["done"]


def test_single_unknown_command_uses_journal_logger(ui, monkeypatch):
    monkeypatch.setattr(commander, "make_dispatch", lambda: {})
    monkeypatch.setattr(commander, "build_header_data", lambda: {})
    monkeypatch.setattr(commander, "print_header", lambda *args, **kwargs: None)
    log = Mock(return_value=None)
    monkeypatch.setattr(commander, "log_free_text", log)
    commander.run_single_command("free text")
    log.assert_called_once_with("free text")


def test_empty_single_command_does_not_dispatch(ui, monkeypatch):
    dispatch = Mock()
    monkeypatch.setattr(commander, "make_dispatch", dispatch)
    monkeypatch.setattr(commander, "build_header_data", lambda: {})
    monkeypatch.setattr(commander, "print_header", lambda *args, **kwargs: None)
    commander.run_single_command("")
    dispatch.assert_not_called()
