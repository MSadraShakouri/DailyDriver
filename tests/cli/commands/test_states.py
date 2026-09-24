from dailydriver.cli.commands import states
from dailydriver.core.state import get_active_numbered_states, start_numbered_state
from dailydriver.core.state.activity import get_last_action_time


def test_start_state_accepts_multiple_categories_and_defaults_to_no_last_update(db_path):
    result = states.start_numbered_state_cmd("st1 Transport/Car friends/a")

    assert "State 1 started" in result
    assert get_last_action_time() is None
    assert get_active_numbered_states()[0]["categories"] == ["transport/car", "friends/a"]


def test_start_state_update_last_flag_can_appear_before_or_after_categories(db_path):
    first = states.start_numbered_state_cmd("st1 -u transport/car")
    assert "last action updated" in first
    first_last = get_last_action_time()
    assert first_last == get_active_numbered_states()[0]["started_at"]

    result = states.start_numbered_state_cmd("st2 friends/a --update-last")
    assert "last action updated" in result
    assert get_last_action_time() == get_active_numbered_states()[1]["started_at"]


def test_end_multiple_states_without_text_stops_them_without_logging_or_touching_last(db_path, monkeypatch):
    start_numbered_state(1, ["friend/b"])
    start_numbered_state(2, ["transport/metro"])
    log = []
    monkeypatch.setattr(states, "log_free_text", lambda *args, **kwargs: log.append((args, kwargs)))

    result = states.end_numbered_states_cmd("et21")

    assert "2, 1" in result
    assert get_active_numbered_states() == []
    assert get_last_action_time() is None
    assert log == []


def test_first_end_id_anchors_combined_log_and_selected_states_stay_active_until_saved(db_path, monkeypatch):
    timestamps = iter((100, 200))
    monkeypatch.setattr("dailydriver.core.state.numbered.time.time", lambda: next(timestamps))
    start_numbered_state(2, ["transport/metro"])
    start_numbered_state(1, ["friends/b"])
    active_seen_during_log = []

    def log(text, started_at=None):
        active_seen_during_log.extend(state["id"] for state in get_active_numbered_states())
        assert text == "arrived together"
        assert started_at == 100  # et21 anchors at state 2, not state 1
        return "logged"

    monkeypatch.setattr(states, "log_free_text", log)
    assert states.end_numbered_states_cmd("et21 arrived together") == "logged"
    assert set(active_seen_during_log) == {1, 2}
    assert get_active_numbered_states() == []


def test_cancelled_final_log_keeps_every_selected_state_active(db_path, ui, monkeypatch):
    start_numbered_state(1, ["one"])
    start_numbered_state(2, ["two"])
    monkeypatch.setattr(states, "log_free_text", lambda *args, **kwargs: None)

    assert states.end_numbered_states_cmd("et12 cancelled") is None
    assert [state["id"] for state in get_active_numbered_states()] == [1, 2]
    assert any("still active" in line for line in ui.lines)


def test_end_rejects_duplicate_or_inactive_slots_without_partial_changes(db_path):
    start_numbered_state(1, ["one"])
    assert "only once" in states.end_numbered_states_cmd("et11")
    assert "not active" in states.end_numbered_states_cmd("et12")
    assert [state["id"] for state in get_active_numbered_states()] == [1]
