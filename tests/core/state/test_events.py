import pytest

from dailydriver.core.state import events


def test_last_action_defaults_to_none_and_reads_value(db_connection):
    from dailydriver.core.state import activity

    assert activity.get_last_action_time() is None
    db_connection.execute("INSERT INTO meta (key, value) VALUES ('last_action', '123')")
    db_connection.commit()
    assert activity.get_last_action_time() == 123


def test_invalid_state_timestamps_are_ignored(db_connection):
    from dailydriver.core.state import activity

    db_connection.executemany(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        [
            ("last_action", "not-a-timestamp"),
            ("pending_start", "also-invalid"),
            ("great_event_start", "bad"),
        ],
    )
    db_connection.commit()

    assert activity.get_last_action_time() is None
    assert events.get_pending_start() is None
    assert events.get_active_great_event() is None


def test_pending_start_save_discard_and_clear(db_path):
    from dailydriver.core.state import activity

    assert events.get_pending_start() is None
    assert activity.get_last_action_time() is None
    assert events.save_pending_start().startswith("Start saved:")
    start_ts = events.get_pending_start()
    assert start_ts > 0
    assert activity.get_last_action_time() == start_ts

    # Discard must NOT update last_action
    assert "discarded" in events.discard_pending_start()
    assert events.get_pending_start() is None
    assert activity.get_last_action_time() == start_ts
    assert events.discard_pending_start() == "No saved start to discard."

    events.save_pending_start()
    events.clear_pending_start()
    assert events.get_pending_start() is None


def test_great_event_lifecycle(db_path):
    from dailydriver.core.state import activity

    timestamp = events.start_great_event(["work", "focus"])
    assert events.get_active_great_event() == (timestamp, ["work", "focus"])
    assert activity.get_last_action_time() == timestamp
    from dailydriver.core.database import get_connection_cm

    with get_connection_cm(auto=False) as conn:
        paths = {row["path"] for row in conn.execute("SELECT path FROM categories")}
    assert paths == {"work", "focus"}
    with pytest.raises(RuntimeError, match="already active"):
        events.start_great_event(["other"])

    # Clear must NOT update last_action
    events.clear_great_event()
    assert events.get_active_great_event() is None
    assert activity.get_last_action_time() == timestamp


def test_update_last_action_persists_timestamp(db_path):
    from dailydriver.core.state import activity

    assert activity.update_last_action().startswith("Last action updated to")
    assert activity.get_last_action_time() > 0
