from unittest.mock import Mock

from dailydriver.cli.commands import events


def test_end_pending_event_requires_start(monkeypatch):
    monkeypatch.setattr(events, "get_pending_start", lambda: None)
    assert events.log_event_end("ee work") == "No running event to end."


def test_end_pending_event_logs_and_clears(monkeypatch):
    log = Mock(return_value="logged")
    clear = Mock()
    monkeypatch.setattr(events, "get_pending_start", lambda: 123)
    monkeypatch.setattr(events, "log_free_text", log)
    monkeypatch.setattr(events, "clear_pending_start", clear)
    assert events.log_event_end("ee work") == "logged"
    log.assert_called_once_with("work", started_at=123)
    clear.assert_called_once_with()


def test_end_pending_event_cancel_keeps_timer_and_warns(ui, monkeypatch):
    # Regression: when logging is cancelled (log_free_text -> None) the running
    # event must stay active AND the user must be told, not silently no-op.
    clear = Mock()
    monkeypatch.setattr(events, "get_pending_start", lambda: 123)
    monkeypatch.setattr(events, "log_free_text", lambda *a, **k: None)
    monkeypatch.setattr(events, "clear_pending_start", clear)
    assert events.log_event_end("ee work") is None
    clear.assert_not_called()
    assert any("still active" in line for line in ui.lines)


def test_chain_uses_last_action(monkeypatch):
    log = Mock(return_value="logged")
    monkeypatch.setattr(events, "get_last_action_time", lambda: 456)
    monkeypatch.setattr(events, "log_free_text", log)
    assert events.log_chain_now("ln follow-up") == "logged"
    log.assert_called_once_with("follow-up", started_at=456)


def test_chain_requires_previous_action(monkeypatch):
    monkeypatch.setattr(events, "get_last_action_time", lambda: None)
    assert events.log_chain_now("ln follow-up") == "No previous action to chain from."


def test_start_great_event_uses_inline_or_interactive_categories(ui, monkeypatch):
    monkeypatch.setattr(events, "get_active_great_event", lambda: None)
    monkeypatch.setattr(events, "start_great_event", lambda categories: 0)
    assert "work, focus" in events.start_great_event_cmd("sge Work Focus")
    ui.queue("project")
    assert "project" in events.start_great_event_cmd("sge")


def test_start_great_event_rejects_active_and_empty(ui, monkeypatch):
    monkeypatch.setattr(events, "get_active_great_event", lambda: (1, ["work"]))
    assert events.start_great_event_cmd("sge other") is None
    assert any("already active" in line for line in ui.lines)

    monkeypatch.setattr(events, "get_active_great_event", lambda: None)
    assert events.start_great_event_cmd("sge") is None
    assert any("No categories" in line for line in ui.lines)


def test_end_great_event_logs_and_clears(monkeypatch):
    log = Mock(return_value="ended")
    clear = Mock()
    monkeypatch.setattr(events, "get_active_great_event", lambda: (500, ["work"]))
    monkeypatch.setattr(events, "log_free_text", log)
    monkeypatch.setattr(events, "clear_great_event", clear)
    assert events.end_great_event_cmd("ege finished") == "ended"
    log.assert_called_once_with("finished", started_at=500)
    clear.assert_called_once_with()


def test_end_great_event_cancel_keeps_event_and_warns(ui, monkeypatch):
    # Regression: the live bug — declining the time confirmation makes
    # log_free_text return None; the great event must remain active AND the
    # user must be warned, instead of the command silently doing nothing.
    clear = Mock()
    monkeypatch.setattr(events, "get_active_great_event", lambda: (500, ["work"]))
    monkeypatch.setattr(events, "log_free_text", lambda *a, **k: None)
    monkeypatch.setattr(events, "clear_great_event", clear)
    assert events.end_great_event_cmd("ege finished") is None
    clear.assert_not_called()
    assert any("still active" in line for line in ui.lines)


def test_cancel_great_event_handles_active_and_inactive(ui, monkeypatch):
    monkeypatch.setattr(events, "get_active_great_event", lambda: None)
    assert events.cancel_great_event_cmd() is None
    assert "No great event active." in ui.lines

    clear = Mock()
    monkeypatch.setattr(events, "get_active_great_event", lambda: (1, []))
    monkeypatch.setattr(events, "clear_great_event", clear)
    assert events.cancel_great_event_cmd() == "Great event cancelled."
    clear.assert_called_once_with()
