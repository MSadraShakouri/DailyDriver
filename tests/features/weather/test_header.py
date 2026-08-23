import time
from datetime import datetime

import jdatetime

from dailydriver.features.weather import header


def test_travel_mode_replaces_weather(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: True)
    assert header.get_weather_str(db_connection, "1405-06-01", True) == "🌍 Travel mode"


def test_today_uses_weather_service(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: False)
    monkeypatch.setattr(
        header,
        "get_weather",
        lambda: {
            "temp_c": 30,
            "condition_fa": "صاف",
            "condition_en": "clear",
            "condition_emoji": "☀️",
            "timestamp": time.time(),
        },
    )
    assert header.get_weather_str(db_connection, "1405-06-01", True) == "☀️ 30°C clear"


def test_stale_today_includes_observation_time(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: False)
    monkeypatch.setattr(
        header,
        "get_weather",
        lambda: {
            "temp_c": 20,
            "condition_fa": "صاف",
            "condition_en": None,
            "condition_emoji": "🌡️",
            "timestamp": 1,
        },
    )
    assert "صاف" in header.get_weather_str(db_connection, "1405-06-01", True)
    assert ":" in header.get_weather_str(db_connection, "1405-06-01", True)


def test_past_day_uses_cached_observation(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: False)
    monkeypatch.setattr(header, "translate_condition", lambda condition: {"en": "clear", "emoji": "☀️"})
    jalali = jdatetime.date(1405, 2, 21)
    gregorian = jalali.togregorian()
    timestamp = int(datetime(gregorian.year, gregorian.month, gregorian.day, 12).timestamp())
    db_connection.execute(
        "INSERT INTO weather_log (city, temp_c, condition_fa, timestamp) VALUES ('Tehran', 25, 'صاف', ?)",
        (timestamp,),
    )
    db_connection.commit()
    assert header.get_weather_str(db_connection, "1405-02-21", False) == "☀️ 25°C clear"


def test_missing_weather_returns_empty_string(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: False)
    monkeypatch.setattr(header, "get_weather", lambda: None)
    assert header.get_weather_str(db_connection, "1405-06-01", True) == ""
