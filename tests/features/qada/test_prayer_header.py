from datetime import datetime

import jdatetime

from dailydriver.features.qada import header

ENTRY = {
    "id": 1,
    "kind": "prayer",
    "slot": "fajr",
    "interval_type": "daily",
    "target_total": 2,
    "logged_total": 0,
    "paused_until": None,
}


def test_prayer_nudges_are_hidden_away_from_today(db_connection):
    yesterday = jdatetime.date.today() - jdatetime.timedelta(days=1)
    assert header.get_prayer_nudges(db_connection, yesterday) == []


def test_prayer_nudges_are_hidden_in_travel_mode(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: True)
    assert header.get_prayer_nudges(db_connection, jdatetime.date.today()) == []


def test_due_prayer_appears_in_one_hour_window(db_connection, monkeypatch):
    today = jdatetime.date.today()
    monkeypatch.setattr(header, "list_entries", lambda kind: [ENTRY])
    monkeypatch.setattr(header, "get_current_pending_instance", lambda entry, date: today)
    monkeypatch.setattr(
        header,
        "get_approximate_times",
        lambda month, day: {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)},
    )
    assert header.get_prayer_nudges(db_connection, today, now=datetime.now().replace(hour=3)) == []
    assert header.get_prayer_nudges(db_connection, today, now=datetime.now().replace(hour=4, minute=1)) == [
        "🕌 Fajr pending"
    ]


def test_overdue_prayer_is_always_visible(db_connection, monkeypatch):
    today = jdatetime.date.today()
    monkeypatch.setattr(header, "list_entries", lambda kind: [ENTRY])
    monkeypatch.setattr(
        header,
        "get_current_pending_instance",
        lambda entry, date: today - jdatetime.timedelta(days=1),
    )
    assert "overdue" in header.get_prayer_nudges(db_connection, today)[0]


def test_unset_prayer_uses_not_set_label(db_connection, monkeypatch):
    today = jdatetime.date.today()
    monkeypatch.setattr(header, "list_entries", lambda kind: [ENTRY | {"target_total": -1}])
    monkeypatch.setattr(header, "get_current_pending_instance", lambda entry, date: today)
    monkeypatch.setattr(
        header,
        "get_approximate_times",
        lambda month, day: {"fajr": (0, 0), "dhuhr": (12, 0), "maghrib": (18, 0)},
    )
    assert "not set" in header.get_prayer_nudges(db_connection, today, now=datetime.now().replace(hour=1))[0]
