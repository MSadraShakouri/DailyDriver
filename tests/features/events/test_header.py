import time

from dailydriver.features.events import header


def test_great_event_status_is_today_only(monkeypatch):
    monkeypatch.setattr(header, "get_active_great_event", lambda: (int(time.time()) - 3600, ["work"]))
    assert "Great Event" in header.get_great_event_str(True)
    assert header.get_great_event_str(False) == ""


def test_running_event_status_is_today_only(monkeypatch):
    monkeypatch.setattr(header, "get_pending_start", lambda: int(time.time()) - 600)
    assert "Event running since" in header.get_running_event_str(True)
    assert header.get_running_event_str(False) == ""


def test_last_entry_time_is_formatted_for_today(monkeypatch):
    monkeypatch.setattr(header, "get_last_action_time", lambda: int(time.time()) - 120)
    value = header.get_last_entry_time(True)
    assert len(value) == 5 and value[2] == ":"
    assert header.get_last_entry_time(False) == ""


def test_missing_state_returns_empty_strings(monkeypatch):
    monkeypatch.setattr(header, "get_active_great_event", lambda: None)
    monkeypatch.setattr(header, "get_pending_start", lambda: None)
    monkeypatch.setattr(header, "get_last_action_time", lambda: None)
    assert header.get_great_event_str(True) == ""
    assert header.get_running_event_str(True) == ""
    assert header.get_last_entry_time(True) == ""
