import pytest

from dailydriver.core.state import events


def test_last_action_defaults_to_none_and_reads_value(db_connection):
    from dailydriver.core.state import activity

    assert activity.get_last_action_time() is None
    db_connection.execute("INSERT INTO meta (key, value) VALUES ('last_action', '123')")
    db_connection.commit()
    assert activity.get_last_action_time() == 123


def test_pending_start_save_discard_and_clear(db_path):
    assert events.get_pending_start() is None
    assert events.save_pending_start().startswith("Start saved:")
    assert events.get_pending_start() > 0
    assert "discarded" in events.discard_pending_start()
    assert events.get_pending_start() is None
    assert events.discard_pending_start() == "No saved start to discard."

    events.save_pending_start()
    events.clear_pending_start()
    assert events.get_pending_start() is None


def test_great_event_lifecycle(db_path):
    timestamp = events.start_great_event(["work", "focus"])
    assert events.get_active_great_event() == (timestamp, ["work", "focus"])
    with pytest.raises(RuntimeError, match="already active"):
        events.start_great_event(["other"])
    events.clear_great_event()
    assert events.get_active_great_event() is None


def test_update_last_action_persists_timestamp(db_path):
    from dailydriver.core.state import activity

    assert activity.update_last_action().startswith("Last action updated to")
    assert activity.get_last_action_time() > 0
