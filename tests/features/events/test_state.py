import pytest

from dailydriver.features.events import state


def test_last_action_defaults_to_none_and_reads_value(db_connection):
    assert state.get_last_action_time() is None
    db_connection.execute("INSERT INTO meta (key, value) VALUES ('last_action', '123')")
    db_connection.commit()
    assert state.get_last_action_time() == 123


def test_pending_start_save_discard_and_clear(db_path):
    assert state.get_pending_start() is None
    assert state.save_pending_start().startswith("Start saved:")
    assert state.get_pending_start() > 0
    assert "discarded" in state.discard_pending_start()
    assert state.get_pending_start() is None
    assert state.discard_pending_start() == "No saved start to discard."

    state.save_pending_start()
    state.clear_pending_start()
    assert state.get_pending_start() is None


def test_great_event_lifecycle(db_path):
    timestamp = state.start_great_event(["work", "focus"])
    assert state.get_active_great_event() == (timestamp, ["work", "focus"])
    with pytest.raises(RuntimeError, match="already active"):
        state.start_great_event(["other"])
    state.clear_great_event()
    assert state.get_active_great_event() is None


def test_update_last_action_persists_timestamp(db_path):
    assert state.update_last_action().startswith("Last action updated to")
    assert state.get_last_action_time() > 0
