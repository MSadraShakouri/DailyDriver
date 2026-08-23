import time

from dailydriver.display.header import events


def test_great_event_status_is_today_only(monkeypatch):
    monkeypatch.setattr(events, "get_active_great_event", lambda: (int(time.time()) - 3600, ["work"]))
    assert "Great Event" in events.get_great_event_str(True)
    assert events.get_great_event_str(False) == ""


def test_running_event_status_is_today_only(monkeypatch):
    monkeypatch.setattr(events, "get_pending_start", lambda: int(time.time()) - 600)
    assert "Event running since" in events.get_running_event_str(True)
    assert events.get_running_event_str(False) == ""


def test_last_entry_time_is_formatted_for_today(monkeypatch):
    monkeypatch.setattr(events, "get_last_action_time", lambda: int(time.time()) - 120)
    value = events.get_last_entry_time(True)
    assert len(value) == 5 and value[2] == ":"
    assert events.get_last_entry_time(False) == ""


def test_missing_state_returns_empty_strings(monkeypatch):
    monkeypatch.setattr(events, "get_active_great_event", lambda: None)
    monkeypatch.setattr(events, "get_pending_start", lambda: None)
    monkeypatch.setattr(events, "get_last_action_time", lambda: None)
    assert events.get_great_event_str(True) == ""
    assert events.get_running_event_str(True) == ""
    assert events.get_last_entry_time(True) == ""
