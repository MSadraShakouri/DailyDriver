from datetime import datetime, time

from unittest.mock import patch

from dailydriver.core.database import get_connection_cm
from dailydriver.features.prayer import commands
from dailydriver.features.prayer.windows import SlotWindow
from dailydriver.utils.time_parser import PrayerArgs


def _fixed_windows():
    """Fajr 04:30-05:55 / Dhuhr 12:00-18:00 / Maghrib 18:20-23:30 on today's date."""
    def win(o_h, o_m, g_h, g_m, r_h, r_m, dl_h, dl_m):
        today = datetime.now().date()
        return SlotWindow(
            opens=datetime.combine(today, time(o_h, o_m)),
            green_until=datetime.combine(today, time(g_h, g_m)),
            red_from=datetime.combine(today, time(r_h, r_m)),
            deadline=datetime.combine(today, time(dl_h, dl_m)),
        )

    return {
        "fajr": win(4, 30, 5, 10, 5, 30, 5, 55),
        "dhuhr_asr": win(12, 0, 15, 30, 16, 30, 18, 0),
        "maghrib_isha": win(18, 20, 19, 30, 21, 30, 23, 30),
    }



def parsed(*, explicit=300, offset=None, jamaat=None, shak=0):
    return PrayerArgs(
        explicit_time=explicit,
        offset_min=offset,
        jamaat_location=jamaat,
        shak_count=shak,
    )


def test_log_prayer_persists_slot_time_and_flags(db_path, ui, monkeypatch):
    monkeypatch.setattr(commands, "parse_prayer_args", lambda args: parsed(jamaat="mosque", shak=2))
    monkeypatch.setattr(commands, "is_travel_mode", lambda: False)
    monkeypatch.setattr(commands, "get_slot_windows", lambda *args, **kwargs: _fixed_windows())
    monkeypatch.setattr(commands, "today_jalali", lambda: "1405-06-01")
    result = commands.log_prayer("p 05:00 j mosque shak 2")
    assert "Logged: Fajr" in result
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT * FROM prayer_logs").fetchone()
    assert row["prayer_slot"] == "fajr"
    assert row["status"] == "on_time"
    assert row["window_band"] == "fadilat"
    assert datetime.fromtimestamp(row["prayer_time"]).strftime("%H:%M") == "05:00"
    assert (row["jamaat_location"], row["shak_count"]) == ("mosque", 2)


def test_log_prayer_classifies_bands_correctly(db_path, ui, monkeypatch):
    monkeypatch.setattr(commands, "is_travel_mode", lambda: False)
    monkeypatch.setattr(commands, "get_slot_windows", lambda *args, **kwargs: _fixed_windows())
    monkeypatch.setattr(commands, "today_jalali", lambda: "1405-06-01")

    # Fajr at 05:20 -> between green_until (05:10) and red_from (05:30) -> normal
    monkeypatch.setattr(commands, "parse_prayer_args", lambda args: parsed(explicit=5 * 60 + 20))
    commands.log_prayer("p 05:20")
    with get_connection_cm(auto=False) as conn:
        row = conn.execute("SELECT window_band, status FROM prayer_logs WHERE prayer_slot='fajr'").fetchone()
    assert (row["window_band"], row["status"]) == ("normal", "on_time")

    # Overwrite with Fajr at 05:40 -> between red_from (05:30) and deadline (05:55) -> late
    monkeypatch.setattr(commands, "parse_prayer_args", lambda args: parsed(explicit=5 * 60 + 40))
    commands.log_prayer("p 05:40")
    with get_connection_cm(auto=False) as conn:
        row = conn.execute("SELECT window_band, status FROM prayer_logs WHERE prayer_slot='fajr'").fetchone()
    assert (row["window_band"], row["status"]) == ("late", "on_time")

    # Overwrite with Fajr at 06:10 -> past deadline (05:55) -> qada
    monkeypatch.setattr(commands, "parse_prayer_args", lambda args: parsed(explicit=6 * 60 + 10))
    commands.log_prayer("p 06:10")
    with get_connection_cm(auto=False) as conn:
        row = conn.execute("SELECT window_band, status FROM prayer_logs WHERE prayer_slot='fajr'").fetchone()
    assert (row["window_band"], row["status"]) == ("qada", "qada")


def test_log_prayer_can_overwrite_same_slot(db_path, ui, monkeypatch):
    monkeypatch.setattr(commands, "parse_prayer_args", lambda args: parsed())
    monkeypatch.setattr(commands, "is_travel_mode", lambda: False)
    monkeypatch.setattr(commands, "get_slot_windows", lambda *args, **kwargs: _fixed_windows())
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
