"""Weather cache service."""

import time

from dailydriver.core.database import get_connection_cm

from .conditions import translate_condition
from .provider import fetch_weather

CACHE_HOURS = 1
_fetch_failed_this_session = False


def _latest_weather(conn):
    return conn.execute(
        "SELECT temp_c, condition_fa, timestamp FROM weather_log ORDER BY id DESC LIMIT 1"
    ).fetchone()


def _store_fresh_weather(conn) -> tuple[int, str] | None:
    global _fetch_failed_this_session
    data = fetch_weather()
    if data is None:
        _fetch_failed_this_session = True
        return None
    temperature, condition = data
    conn.execute(
        "INSERT INTO weather_log (city, temp_c, condition_fa, timestamp) VALUES (?,?,?,?)",
        ("Tehran", temperature, condition, int(time.time())),
    )
    conn.commit()
    return data


def _result(temperature: int, condition: str, timestamp: int) -> dict:
    translation = translate_condition(condition)
    return {
        "temp_c": temperature,
        "condition_fa": condition,
        "condition_en": translation["en"] if translation else None,
        "condition_emoji": translation["emoji"] if translation else "🌡️",
        "city": "Tehran",
        "timestamp": timestamp,
    }


def get_weather() -> dict | None:
    """Return fresh weather when possible, otherwise the latest cached value."""
    global _fetch_failed_this_session
    with get_connection_cm(auto=False) as conn:
        cached = _latest_weather(conn)
        if _fetch_failed_this_session:
            return _result(cached["temp_c"], cached["condition_fa"], cached["timestamp"]) if cached else None

        now = int(time.time())
        if cached is None or now - cached["timestamp"] > CACHE_HOURS * 3600:
            fresh = _store_fresh_weather(conn)
            if fresh is not None:
                temperature, condition = fresh
                return _result(temperature, condition, now)
            if cached is None:
                return None

        return _result(cached["temp_c"], cached["condition_fa"], cached["timestamp"])
