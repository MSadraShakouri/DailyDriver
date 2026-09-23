import time
from datetime import datetime, timedelta

import jdatetime

from dailydriver.core.location.resolver import CityInfo
from dailydriver.features.weather import header


def _info(name="Tehran", reason="default", until=None):
    return CityInfo(name=name, lat=35.689198, lon=51.388974, tz=3.5, weather_url="http://x", reason=reason, until=until)


def _weather(**overrides):
    data = {
        "temp_c": 30,
        "condition_fa": "صاف",
        "condition_en": "clear",
        "condition_emoji": "☀️",
        "timestamp": time.time(),
    }
    data.update(overrides)
    return data


def test_travel_mode_replaces_weather(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: True)
    assert header.get_weather_str(db_connection, "1405-06-01", True) == "🌍 Travel mode"


def test_today_uses_weather_service_and_shows_the_resolved_city(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: False)
    monkeypatch.setattr(header, "get_weather", lambda city=None: _weather())
    assert header.get_weather_str(db_connection, "1405-06-01", True) == "☀️ 30°C clear (Tehran)"


def test_city_suffix_follows_the_resolved_city(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: False)
    monkeypatch.setattr(header, "resolve_city", lambda conn: _info("Karaj"))
    monkeypatch.setattr(header, "get_weather", lambda city=None: _weather())
    assert header.get_weather_str(db_connection, "1405-06-01", True) == "☀️ 30°C clear (Karaj)"
    # The resolved city (not anything else) is what the service receives.
    received = {}
    monkeypatch.setattr(
        header,
        "get_weather",
        lambda city=None: (received.update(name=city.name), _weather())[1],
    )
    header.get_weather_str(db_connection, "1405-06-01", True)
    assert received["name"] == "Karaj"


def test_schedule_city_shows_until_when_the_rule_ends_soon(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: False)
    soon = datetime.now().replace(hour=18, minute=0, second=0, microsecond=0) + timedelta(days=1)
    soon = datetime.now() + timedelta(minutes=90)
    monkeypatch.setattr(header, "resolve_city", lambda conn: _info("Karaj", "schedule", until=soon))
    monkeypatch.setattr(header, "get_weather", lambda city=None: _weather())
    line = header.get_weather_str(db_connection, "1405-06-01", True)
    assert line == f"☀️ 30°C clear (Karaj, until {soon.strftime('%H:%M')})"


def test_schedule_city_without_upcoming_handover_shows_plain_suffix(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: False)
    far = datetime.now() + timedelta(hours=5)
    monkeypatch.setattr(header, "resolve_city", lambda conn: _info("Karaj", "schedule", until=far))
    monkeypatch.setattr(header, "get_weather", lambda city=None: _weather())
    assert header.get_weather_str(db_connection, "1405-06-01", True) == "☀️ 30°C clear (Karaj)"


def test_stale_today_includes_observation_time(db_connection, monkeypatch):
    monkeypatch.setattr(header, "is_travel_mode", lambda: False)
    monkeypatch.setattr(
        header,
        "get_weather",
        lambda city=None: {
            "temp_c": 20,
            "condition_fa": "صاف",
            "condition_en": None,
            "condition_emoji": "🌡️",
            "timestamp": 1,
        },
    )
    assert "صاف" in header.get_weather_str(db_connection, "1405-06-01", True)
    assert ":" in header.get_weather_str(db_connection, "1405-06-01", True)


def test_past_day_uses_cached_observation_without_city_suffix(db_connection, monkeypatch):
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
