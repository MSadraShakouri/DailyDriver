import time
from datetime import datetime

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


def _at(hhmm: str) -> int:
    """Return a timestamp whose local ``%H:%M`` rendering is *hhmm*."""
    return int(datetime.strptime(hhmm, "%H:%M").replace(year=2026, month=5, day=4).timestamp())


def test_numbered_states_render_one_compact_line_per_slot(monkeypatch):
    monkeypatch.setattr(events, "get_width", lambda: 80)
    monkeypatch.setattr(
        events,
        "get_active_numbered_states",
        lambda: [
            {"id": 1, "started_at": _at("09:00"), "categories": ["work"]},
            {"id": 3, "started_at": _at("09:05"), "categories": ["friends/b", "food/lunch"]},
        ],
    )
    assert events.get_numbered_states_lines(True) == [
        "⏱ 1 work · 09:00",
        "⏱ 3 friends/b food/lunch · 09:05",
    ]


def test_numbered_states_are_hidden_for_past_days_and_when_inactive(monkeypatch):
    monkeypatch.setattr(events, "get_active_numbered_states", lambda: [{"id": 1, "started_at": 0, "categories": ["w"]}])
    assert events.get_numbered_states_lines(False) == []
    monkeypatch.setattr(events, "get_active_numbered_states", lambda: [])
    assert events.get_numbered_states_lines(True) == []


def test_long_category_names_never_strand_the_time_separator(monkeypatch):
    """Regression: a single over-long path must not leave a dangling ``·`` row."""
    monkeypatch.setattr(events, "get_width", lambda: 50)
    monkeypatch.setattr(
        events,
        "get_active_numbered_states",
        lambda: [
            {
                "id": 2,
                "started_at": _at("13:23"),
                "categories": ["work/coding/very-long-category-name-here"],
            }
        ],
    )
    assert events.get_numbered_states_lines(True) == [
        "⏱ 2 work/coding/very-long-category-name-here",
        "    · 13:23",
    ]


def test_several_categories_wrap_under_a_hanging_indent(monkeypatch):
    monkeypatch.setattr(events, "get_width", lambda: 24)
    monkeypatch.setattr(
        events,
        "get_active_numbered_states",
        lambda: [{"id": 4, "started_at": _at("13:23"), "categories": ["friends/b", "food/lunch"]}],
    )
    assert events.get_numbered_states_lines(True) == [
        "⏱ 4 friends/b",
        "    food/lunch · 13:23",
    ]
