from datetime import datetime

import jdatetime

from dailydriver.features.prayer import backlog
from dailydriver.features.prayer.schedule import PRAYER_SLOTS


def _set_complete(connection, date):
    connection.execute(
        "INSERT OR REPLACE INTO meta (key, value) VALUES ('prayer_complete_until', ?)",
        (date.strftime("%Y-%m-%d"),),
    )
    connection.commit()


def _log_slots(connection, date, slots=PRAYER_SLOTS):
    for slot in slots:
        connection.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status) VALUES (?, ?, 'on_time')",
            (slot, date.strftime("%Y-%m-%d")),
        )
    connection.commit()


def test_complete_until_advances_through_full_days(db_connection):
    today = jdatetime.date.today()
    yesterday = today - jdatetime.timedelta(days=1)
    _set_complete(db_connection, yesterday)
    _log_slots(db_connection, yesterday)
    _log_slots(db_connection, today)
    backlog._update_complete_until(db_connection)
    assert backlog._get_complete_until(db_connection) == today.strftime("%Y-%m-%d")


def test_complete_until_stops_at_incomplete_day(db_connection):
    today = jdatetime.date.today()
    yesterday = today - jdatetime.timedelta(days=1)
    _set_complete(db_connection, yesterday)
    _log_slots(db_connection, yesterday)
    _log_slots(db_connection, today, ["fajr"])
    backlog._update_complete_until(db_connection)
    assert backlog._get_complete_until(db_connection) == yesterday.strftime("%Y-%m-%d")


def test_empty_history_initializes_to_today(db_connection, monkeypatch):
    today = jdatetime.date.today().strftime("%Y-%m-%d")
    monkeypatch.setattr(backlog, "today_jalali", lambda: today)
    backlog._update_complete_until(db_connection)
    assert backlog._get_complete_until(db_connection) == today


def test_unlogged_slots_only_include_prayers_whose_time_has_passed(db_connection, monkeypatch):
    today = jdatetime.date.today()
    _set_complete(db_connection, today - jdatetime.timedelta(days=1))
    monkeypatch.setattr(
        backlog,
        "get_approximate_times",
        lambda month, day: {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)},
    )
    gregorian = today.togregorian()
    now = datetime(gregorian.year, gregorian.month, gregorian.day, 13)
    assert backlog._get_unlogged_past_slots(db_connection, now) == [
        (today.strftime("%Y-%m-%d"), "fajr"),
        (today.strftime("%Y-%m-%d"), "dhuhr_asr"),
    ]


def test_log_qada_uses_selected_missing_slot(db_connection, ui, monkeypatch):
    date = (jdatetime.date.today() - jdatetime.timedelta(days=1)).strftime("%Y-%m-%d")
    monkeypatch.setattr(backlog, "_get_unlogged_past_slots", lambda connection: [(date, "fajr")])
    monkeypatch.setattr(backlog, "_update_complete_until", lambda connection: None)
    ui.queue("")
    backlog.log_qada(time_of_day_minutes=5 * 60 + 30)
    row = db_connection.execute("SELECT prayer_slot, jalali_date, status, prayer_time FROM prayer_logs").fetchone()
    assert tuple(row)[:3] == ("fajr", date, "qada")
    assert datetime.fromtimestamp(row["prayer_time"]).strftime("%H:%M") == "05:30"
