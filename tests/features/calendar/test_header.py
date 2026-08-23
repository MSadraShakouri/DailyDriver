from unittest.mock import patch

import jdatetime

from dailydriver.features import calendar
from dailydriver.features.calendar import header
from dailydriver.features.registry import validate_header_sections


def event(title, *, calendar_name="jalali", holiday=False, identifier=1):
    return {"id": identifier, "calendar": calendar_name, "holiday": holiday, "title_en": title}


def test_today_and_past_lines_use_calendar_icons(monkeypatch):
    date = jdatetime.date(1405, 6, 1)
    monkeypatch.setattr(header.catalog, "get_events", lambda: [])
    monkeypatch.setattr(header.catalog, "get_todays_events", lambda events: [event("Today")])
    assert header.get_calendar_lines(date, True) == [("🔆 ", "Today")]

    monkeypatch.setattr(
        header.catalog,
        "get_events_for_date",
        lambda target: [event("Christmas", calendar_name="gregorian", holiday=True)],
    )
    assert header.get_calendar_lines(date, False) == [("🌐🎊 ", "Christmas")]


def test_reminded_ids_are_suppressed(monkeypatch):
    date = jdatetime.date(1405, 6, 1)
    monkeypatch.setattr(header.catalog, "get_events", lambda: [])
    monkeypatch.setattr(
        header.catalog,
        "get_todays_events",
        lambda events: [event("Hidden", identifier=1), event("Visible", identifier=2)],
    )
    assert header.get_calendar_lines(date, True, reminded_ids={1}) == [("🔆 ", "Visible")]


def test_feature_hook_wraps_structured_line(db_connection):
    date = jdatetime.date.today()
    with patch(
        "dailydriver.features.calendar.catalog.get_events",
        return_value=[(date, event("Test Day"))],
    ):
        sections = calendar.header_sections(db_connection, date.strftime("%Y-%m-%d"), date, True)
    assert (46, ("🔆 ", "Test Day")) in sections
    assert validate_header_sections(calendar, sections) == sections
