import time

import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.core.location.resolver import CityInfo
from dailydriver.features.weather import service


def _info(name, url="https://weather.example/page"):
    return CityInfo(name=name, lat=35.0, lon=51.0, tz=3.5, weather_url=url, reason="default")


@pytest.fixture(autouse=True)
def reset_session_failure():
    service._fetch_failed_this_session = False
    yield
    service._fetch_failed_this_session = False


@pytest.fixture
def translated(monkeypatch):
    monkeypatch.setattr(service, "translate_condition", lambda condition: {"en": "clear", "emoji": "☀️"})


def _insert_weather(timestamp):
    with get_connection_cm(auto=False) as connection:
        connection.execute(
            "INSERT INTO weather_log (city, temp_c, condition_fa, timestamp) VALUES ('Tehran', 20, 'صاف', ?)",
            (timestamp,),
        )
        connection.commit()


def test_fresh_fetch_is_stored(db_path, translated, monkeypatch):
    monkeypatch.setattr(service, "fetch_weather", lambda url=None: (28, "صاف"))
    result = service.get_weather()
    assert (result["temp_c"], result["condition_en"], result["condition_emoji"]) == (28, "clear", "☀️")
    with get_connection_cm(auto=False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM weather_log").fetchone()[0] == 1


def test_recent_cache_skips_network(db_path, translated, monkeypatch):
    _insert_weather(int(time.time()))
    called = False

    def fetch(url=None):
        nonlocal called
        called = True

    monkeypatch.setattr(service, "fetch_weather", fetch)
    assert service.get_weather()["temp_c"] == 20
    assert not called


def test_failed_refresh_falls_back_to_stale_cache(db_path, translated, monkeypatch):
    _insert_weather(1)
    monkeypatch.setattr(service, "fetch_weather", lambda url=None: None)
    assert service.get_weather()["temp_c"] == 20
    assert service._fetch_failed_this_session


def test_failed_refresh_without_cache_returns_none(db_path, translated, monkeypatch):
    monkeypatch.setattr(service, "fetch_weather", lambda url=None: None)
    assert service.get_weather() is None
    assert service.get_weather() is None


def test_cache_is_scoped_per_city(db_path, translated, monkeypatch):
    _insert_weather(int(time.time()))  # a fresh Tehran row
    calls = []

    def fetch(url=None):
        calls.append(url)
        return (12, "صاف")

    monkeypatch.setattr(service, "fetch_weather", fetch)
    karaj = service.get_weather(_info("Karaj"))
    assert (karaj["temp_c"], karaj["city"]) == (12, "Karaj")
    assert len(calls) == 1
    # Tehran's fresh cache is still used: no additional fetch for it.
    tehran = service.get_weather(_info("Tehran"))
    assert (tehran["temp_c"], tehran["city"]) == (20, "Tehran")
    assert len(calls) == 1


def test_city_without_weather_url_is_suppressed(db_path, translated, monkeypatch):
    calls = []
    monkeypatch.setattr(service, "fetch_weather", lambda url=None: calls.append(url))
    assert service.get_weather(_info("Yazd", url=None)) is None
    assert calls == []
    with get_connection_cm(auto=False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM weather_log").fetchone()[0] == 0


def test_stored_rows_carry_the_city_name(db_path, translated, monkeypatch):
    monkeypatch.setattr(service, "fetch_weather", lambda url=None: (9, "بارانی"))
    service.get_weather(_info("Mashhad"))
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT city, temp_c FROM weather_log").fetchone()
    assert (row["city"], row["temp_c"]) == ("Mashhad", 9)
