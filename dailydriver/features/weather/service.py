"""Weather cache service, scoped per resolved city."""

import time

from dailydriver.core.database import get_connection_cm
from dailydriver.core.location.resolver import resolve_city

from .conditions import translate_condition
from .provider import fetch_weather

CACHE_HOURS = 1
_fetch_failed_this_session = False


def _latest_weather(conn, city_name):
    return conn.execute(
        "SELECT temp_c, condition_fa, timestamp FROM weather_log WHERE city = ? ORDER BY id DESC LIMIT 1",
        (city_name,),
    ).fetchone()


def _store_fresh_weather(conn, city):
    global _fetch_failed_this_session
    url = getattr(city, "weather_url", None)
    if not url:
        # No IRIMO page for this city: the weather line is suppressed.
        return None
    data = fetch_weather(url)
    if data is None:
        _fetch_failed_this_session = True
        return None
    temperature, condition = data
    conn.execute(
        "INSERT INTO weather_log (city, temp_c, condition_fa, timestamp) VALUES (?,?,?,?)",
        (city.name, temperature, condition, int(time.time())),
    )
    conn.commit()
    return data


def _result(temperature: int, condition: str, timestamp: int, city_name: str) -> dict:
    translation = translate_condition(condition)
    return {
        "temp_c": temperature,
        "condition_fa": condition,
        "condition_en": translation["en"] if translation else None,
        "condition_emoji": translation["emoji"] if translation else "🌡️",
        "city": city_name,
        "timestamp": timestamp,
    }


def get_weather(city=None) -> dict | None:
    """Return fresh weather for *city* when possible, else that city's cached value.

    ``city`` is anything with ``name`` and ``weather_url`` (normally the
    resolved CityInfo); ``None`` resolves the active city.
    """
    global _fetch_failed_this_session
    with get_connection_cm(auto=False) as conn:
        if city is None:
            city = resolve_city(conn)
        cached = _latest_weather(conn, city.name)
        if _fetch_failed_this_session:
            return _result(cached["temp_c"], cached["condition_fa"], cached["timestamp"], city.name) if cached else None

        now = int(time.time())
        if cached is None or now - cached["timestamp"] > CACHE_HOURS * 3600:
            fresh = _store_fresh_weather(conn, city)
            if fresh is not None:
                temperature, condition = fresh
                return _result(temperature, condition, now, city.name)
            if cached is None:
                return None

        return _result(cached["temp_c"], cached["condition_fa"], cached["timestamp"], city.name)
