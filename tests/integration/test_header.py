"""The complete header pipeline runs every enabled feature contract."""

from unittest.mock import patch

import jdatetime

from dailydriver.core.travel_mode import set_travel_mode
from dailydriver.display.header import build_header_data
from dailydriver.features.registry import validate_header_sections


def test_header_builds_from_fully_migrated_database(db_path):
    set_travel_mode(True)  # prevents network weather and location-dependent prayer work
    data = build_header_data()
    assert {
        "jalali_line",
        "separator",
        "greg_hijri_line",
        "feature_lines",
        "is_today",
        "last_entry_time",
    } <= data.keys()
    assert data["is_today"] is True
    assert all(isinstance(line, (str, tuple)) for line in data["feature_lines"])


def test_active_great_and_running_events_appear_in_header(db_path):
    """Regression: great-event and running-event status must be built into the
    header's feature_lines, not just exist as orphan helper functions."""
    from dailydriver.core.state import save_pending_start, start_great_event

    set_travel_mode(True)
    start_great_event(["work"])
    save_pending_start()
    data = build_header_data()
    lines = data["feature_lines"]
    assert any(isinstance(l, str) and "Great Event" in l for l in lines)
    assert any(isinstance(l, str) and "Event running since" in l for l in lines)


def test_event_lines_render_above_sleep_below_prayer(db_path):
    """Events keep their historic slot: after prayer (priority 0) and before
    sleep (priority 10), matching the pre-refactor placement."""
    from dailydriver.core.state import save_pending_start, start_great_event

    set_travel_mode(True)
    start_great_event(["work"])
    save_pending_start()
    lines = [l for l in build_header_data()["feature_lines"] if isinstance(l, str)]

    def index_where(predicate):
        return next((i for i, l in enumerate(lines) if predicate(l)), None)

    prayer_i = index_where(lambda l: "🕌" in l)
    great_i = index_where(lambda l: "Great Event" in l)
    running_i = index_where(lambda l: "Event running since" in l)
    sleep_i = index_where(lambda l: "💤" in l or "😴" in l)

    assert great_i is not None and running_i is not None
    if prayer_i is not None:
        assert prayer_i < great_i < running_i
    if sleep_i is not None:
        assert running_i < sleep_i


def test_structured_calendar_line_survives_registry_and_header_pipeline(db_path):
    set_travel_mode(True)
    today = jdatetime.date.today()
    event = {
        "id": 9001,
        "calendar": "jalali",
        "holiday": False,
        "title_en": "Integration Event",
    }
    with patch("dailydriver.features.calendar.catalog.get_events", return_value=[(today, event)]):
        data = build_header_data()
    assert ("🔆 ", "Integration Event") in data["feature_lines"]


def test_each_enabled_header_hook_returns_valid_sections(db_connection):
    import dailydriver.features as features

    today = jdatetime.date.today()
    date_string = today.strftime("%Y-%m-%d")
    set_travel_mode(True)
    for feature in features.ENABLED:
        hook = getattr(feature, "header_sections", None)
        if hook is None:
            continue
        returned = hook(db_connection, date_string, today, True)
        assert validate_header_sections(feature, returned) == returned
