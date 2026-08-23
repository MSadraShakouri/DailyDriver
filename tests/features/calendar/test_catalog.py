import json
import jdatetime

from dailydriver.features.calendar import catalog


def test_load_json_handles_missing_and_existing_files(tmp_path):
    path = tmp_path / "events.json"
    assert catalog._load_json(path) == []
    path.write_text(json.dumps([{"title_en": "Event"}]))
    assert catalog._load_json(path) == [{"title_en": "Event"}]


def test_convert_events_combines_calendars_and_deduplicates(tmp_path, monkeypatch):
    jalali = tmp_path / "jalali.json"
    gregorian = tmp_path / "gregorian.json"
    hijri = tmp_path / "hijri.json"
    jalali.write_text(json.dumps([{"month": 1, "day": 1, "title_en": "Nowruz"}]))
    gregorian.write_text(json.dumps([{"month": 3, "day": 21, "title_en": "March"}]))
    hijri.write_text("[]")
    monkeypatch.setattr(catalog, "JALALI_FILE", str(jalali))
    monkeypatch.setattr(catalog, "GREGORIAN_FILE", str(gregorian))
    monkeypatch.setattr(catalog, "HIJRI_FILE", str(hijri))
    converted = catalog._convert_all_events(1405)
    assert {event["title_en"] for _, event in converted} == {"Nowruz", "March"}
    assert all(isinstance(day, jdatetime.date) for day, _ in converted)


def test_event_queries_filter_and_sort_supplied_events():
    today = jdatetime.date.today()
    events = [
        (today + jdatetime.timedelta(days=2), {"title_en": "Later"}),
        (today, {"title_en": "Today"}),
        (today + jdatetime.timedelta(days=1), {"title_en": "Soon"}),
    ]
    assert [event["title_en"] for event in catalog.get_todays_events(events)] == ["Today"]
    assert [event["title_en"] for _, event in catalog.get_upcoming_events(events, days=2)] == [
        "Today",
        "Soon",
        "Later",
    ]


def test_cache_refreshes_once_per_jalali_year(monkeypatch):
    calls = []
    monkeypatch.setattr(catalog, "_convert_all_events", lambda year: calls.append(year) or [])
    catalog.invalidate_cache()
    assert catalog.get_events() == []
    assert catalog.get_events() == []
    assert calls == [jdatetime.date.today().year]
