from datetime import datetime
from unittest.mock import patch

from dailydriver.core.database import get_connection_cm
from dailydriver.features.prayer import commands


def parsed(*, explicit=300, offset=None, jamaat=None, shak=0):
    return {
        "explicit_time": explicit,
        "offset_min": offset,
        "jamaat_location": jamaat,
        "shak_count": shak,
    }


def test_log_prayer_persists_slot_time_and_flags(db_path, ui, monkeypatch):
    monkeypatch.setattr(commands, "parse_prayer_args", lambda args: parsed(jamaat="mosque", shak=2))
    monkeypatch.setattr(commands, "is_travel_mode", lambda: False)
    monkeypatch.setattr(
        commands,
        "get_approximate_times",
        lambda month, day: {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)},
    )
    monkeypatch.setattr(commands, "today_jalali", lambda: "1405-06-01")
    result = commands.log_prayer("p 05:00 j mosque shak 2")
    assert "Logged: Fajr" in result
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT * FROM prayer_logs").fetchone()
    assert row["prayer_slot"] == "fajr"
    assert datetime.fromtimestamp(row["prayer_time"]).strftime("%H:%M") == "05:00"
    assert (row["jamaat_location"], row["shak_count"]) == ("mosque", 2)


def test_log_prayer_can_overwrite_same_slot(db_path, ui, monkeypatch):
    monkeypatch.setattr(commands, "parse_prayer_args", lambda args: parsed())
    monkeypatch.setattr(commands, "is_travel_mode", lambda: False)
    monkeypatch.setattr(
        commands,
        "get_approximate_times",
        lambda month, day: {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)},
    )
    monkeypatch.setattr(commands, "today_jalali", lambda: "1405-06-01")
    commands.log_prayer("p")
    commands.log_prayer("p")
    with get_connection_cm(auto=False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM prayer_logs").fetchone()[0] == 1


def test_confirmation_can_cancel_without_write(db_path, monkeypatch):
    monkeypatch.setattr(commands, "parse_prayer_args", lambda args: parsed())
    monkeypatch.setattr(commands, "is_travel_mode", lambda: False)
    monkeypatch.setattr(commands.current_ui, "confirm", lambda *args, **kwargs: False)
    assert commands.log_prayer("p") is None
    with get_connection_cm(auto=False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM prayer_logs").fetchone()[0] == 0


def test_qada_flag_delegates_to_backlog(db_path, monkeypatch):
    monkeypatch.setattr(commands, "parse_prayer_args", lambda args: parsed(explicit=300, offset=15))
    with patch("dailydriver.features.prayer.backlog.log_qada") as log_qada:
        assert commands.log_prayer("p q 05:00") is None
    log_qada.assert_called_once_with(300, 15)
