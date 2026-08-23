import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.features.prayer import commands


def _log_slot(connection, slot, date="1405-06-01"):
    connection.execute(
        "INSERT INTO prayer_logs (prayer_slot, jalali_date, status) VALUES (?, ?, 'on_time')",
        (slot, date),
    )
    connection.commit()


def test_travel_selector_suggests_first_unlogged_slot(db_connection, ui):
    ui.queue("")
    assert commands._travel_mode_select_slot(db_connection, "1405-06-01") == "fajr"
    _log_slot(db_connection, "fajr")
    ui.queue("")
    assert commands._travel_mode_select_slot(db_connection, "1405-06-01") == "dhuhr_asr"


@pytest.mark.parametrize(
    ("choice", "slot"),
    [("1", "fajr"), ("f", "fajr"), ("2", "dhuhr_asr"), ("dhuhr", "dhuhr_asr"), ("3", "maghrib_isha")],
)
def test_travel_selector_accepts_explicit_choices(db_connection, ui, choice, slot):
    ui.queue(choice)
    assert commands._travel_mode_select_slot(db_connection, "1405-06-01") == slot


def test_travel_selector_can_cancel_or_fall_back(db_connection, ui):
    ui.queue("n")
    assert commands._travel_mode_select_slot(db_connection, "1405-06-01") is None
    ui.queue("invalid")
    assert commands._travel_mode_select_slot(db_connection, "1405-06-01") == "fajr"
    assert "Invalid choice. Using default." in ui.lines


def test_log_prayer_uses_travel_selected_slot(db_path, ui, monkeypatch):
    ui.queue("3")
    monkeypatch.setattr(commands, "is_travel_mode", lambda: True)
    monkeypatch.setattr(commands, "today_jalali", lambda: "1405-06-01")
    monkeypatch.setattr(
        commands,
        "parse_prayer_args",
        lambda args: {"offset_min": None, "explicit_time": 300, "jamaat_location": None, "shak_count": 0},
    )
    assert "Maghrib & Isha" in commands.log_prayer("p 05:00")
    with get_connection_cm(auto=False) as connection:
        assert connection.execute("SELECT prayer_slot FROM prayer_logs").fetchone()[0] == "maghrib_isha"
