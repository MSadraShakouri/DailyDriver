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
