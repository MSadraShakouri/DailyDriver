import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.core.state import (
    clear_numbered_states,
    get_active_injected_categories,
    get_active_numbered_states,
    start_great_event,
    start_numbered_state,
)
from dailydriver.core.state.activity import get_last_action_time


def test_start_state_creates_multiple_categories_without_touching_last_action(db_path):
    assert get_last_action_time() is None

    timestamp = start_numbered_state(1, ["Transport/Car", "friends/a", "transport/car"])

    assert get_last_action_time() is None
    assert get_active_numbered_states() == [
        {"id": 1, "started_at": timestamp, "categories": ["transport/car", "friends/a"]}
    ]
    with get_connection_cm(auto=False) as conn:
        paths = {row["path"] for row in conn.execute("SELECT path FROM categories")}
    assert paths == {"transport/car", "friends/a"}


def test_start_state_update_last_is_opt_in_and_uses_state_start_time(db_path):
    timestamp = start_numbered_state(2, ["work/coding"], update_last=True)
    assert get_last_action_time() == timestamp


def test_state_slots_are_limited_and_cannot_overwrite_an_active_state(db_path):
    with pytest.raises(ValueError, match="1 to 9"):
        start_numbered_state(0, ["zero"])
    with pytest.raises(ValueError, match="1 to 9"):
        start_numbered_state(10, ["ten"])
    with pytest.raises(ValueError, match="At least one category"):
        start_numbered_state(1, [])

    start_numbered_state(1, ["work"])
    with pytest.raises(RuntimeError, match="already active"):
        start_numbered_state(1, ["other"])


def test_duplicate_existing_categories_do_not_advance_category_sequence(db_path):
    start_numbered_state(1, ["work"])
    with get_connection_cm(auto=False) as conn:
        first_seq = conn.execute("SELECT seq FROM sqlite_sequence WHERE name='categories'").fetchone()[0]

    start_numbered_state(2, ["work"])
    with get_connection_cm(auto=False) as conn:
        second_seq = conn.execute("SELECT seq FROM sqlite_sequence WHERE name='categories'").fetchone()[0]
        assert conn.execute("SELECT COUNT(*) FROM categories WHERE path='work'").fetchone()[0] == 1
    assert second_seq == first_seq


def test_end_states_clears_only_selected_slots_and_does_not_touch_last_action(db_path):
    start_numbered_state(1, ["work"])
    start_numbered_state(2, ["friend/a"])
    clear_numbered_states([1])

    assert [state["id"] for state in get_active_numbered_states()] == [2]
    assert get_last_action_time() is None


def test_injected_categories_union_numbered_states_and_legacy_great_event(db_path):
    start_numbered_state(1, ["work", "friend/a"])
    start_numbered_state(2, ["friend/a", "transport/metro"])
    start_great_event(["work", "legacy/event"])

    assert get_active_injected_categories() == [
        "work",
        "legacy/event",
        "friend/a",
        "transport/metro",
    ]
