import time

import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.features.weather import service


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
    monkeypatch.setattr(service, "fetch_weather", lambda: (28, "صاف"))
    result = service.get_weather()
    assert (result["temp_c"], result["condition_en"], result["condition_emoji"]) == (28, "clear", "☀️")
    with get_connection_cm(auto=False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM weather_log").fetchone()[0] == 1


def test_recent_cache_skips_network(db_path, translated, monkeypatch):
    _insert_weather(int(time.time()))
    called = False

    def fetch():
        nonlocal called
        called = True

    monkeypatch.setattr(service, "fetch_weather", fetch)
    assert service.get_weather()["temp_c"] == 20
    assert not called


def test_failed_refresh_falls_back_to_stale_cache(db_path, translated, monkeypatch):
    _insert_weather(1)
    monkeypatch.setattr(service, "fetch_weather", lambda: None)
    assert service.get_weather()["temp_c"] == 20
    assert service._fetch_failed_this_session


def test_failed_refresh_without_cache_returns_none(db_path, translated, monkeypatch):
    monkeypatch.setattr(service, "fetch_weather", lambda: None)
    assert service.get_weather() is None
    assert service.get_weather() is None
