from datetime import datetime

import jdatetime

from dailydriver.features.prayer import nudges


def _times(month, day):
    return {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)}


def test_nudges_are_hidden_for_non_today(db_connection):
    date = jdatetime.date(1405, 6, 1)
    assert nudges.get_prayer_nudges(db_connection, date, "1405-06-01", False) == []


def test_prealert_and_overdue_today(db_connection, monkeypatch):
    date = jdatetime.date.today()
    monkeypatch.setattr(nudges, "is_travel_mode", lambda: False)
    monkeypatch.setattr(nudges, "get_approximate_times", _times)
    before_fajr = datetime.now().replace(hour=4, minute=30, second=0, microsecond=0)
    lines = nudges.get_prayer_nudges(db_connection, date, date.strftime("%Y-%m-%d"), True, now=before_fajr)
    assert any("Fajr in ~30 min" in line for line in lines)

    after_maghrib = datetime.now().replace(hour=20, minute=0, second=0, microsecond=0)
    lines = nudges.get_prayer_nudges(db_connection, date, date.strftime("%Y-%m-%d"), True, now=after_maghrib)
    assert any("Maghrib" in line and "not logged" in line for line in lines)


def test_logged_slot_is_not_marked_overdue(db_connection, monkeypatch):
    date = jdatetime.date.today()
    date_str = date.strftime("%Y-%m-%d")
    db_connection.execute(
        "INSERT INTO prayer_logs (prayer_slot, jalali_date, status) VALUES ('fajr', ?, 'on_time')",
        (date_str,),
    )
    db_connection.commit()
    monkeypatch.setattr(nudges, "is_travel_mode", lambda: False)
    monkeypatch.setattr(nudges, "get_approximate_times", _times)
    now = datetime.now().replace(hour=6, minute=0, second=0, microsecond=0)
    lines = nudges.get_prayer_nudges(db_connection, date, date_str, True, now)
    assert not any("Fajr not logged (today)" in line for line in lines)


def test_travel_mode_shows_first_unlogged_slot(db_connection, monkeypatch):
    date = jdatetime.date.today()
    date_str = date.strftime("%Y-%m-%d")
    monkeypatch.setattr(nudges, "is_travel_mode", lambda: True)
    assert "Fajr not logged" in nudges.get_prayer_nudges(db_connection, date, date_str, True)[0]
    db_connection.execute(
        "INSERT INTO prayer_logs (prayer_slot, jalali_date, status) VALUES ('fajr', ?, 'on_time')",
        (date_str,),
    )
    db_connection.commit()
    assert "Dhuhr" in nudges.get_prayer_nudges(db_connection, date, date_str, True)[0]
