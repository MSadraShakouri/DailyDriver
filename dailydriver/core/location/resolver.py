"""City resolution with the precedence: travel > override > schedule > default.

:func:`resolve_city` is a pure function: no UI, no side effects, safe to
call from any feature with an open connection.  An expired override is
ignored rather than deleted (deleting is the manager's job), so the
schedule -- or the default city where no rule applies -- governs from the
expiry minute onward and nothing lingers.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from dailydriver.core.location import state as city_state
from dailydriver.core.location.registry import DEFAULT_CITY_NAME, City, load_registry
from dailydriver.core.location.rules import MINUTES_PER_DAY, active_rule, iranian_weekday, list_rules


@dataclass(frozen=True)
class CityInfo:
    """The resolved city plus why it won and when it will hand over."""

    name: str
    lat: float
    lon: float
    tz: float
    weather_url: str | None
    reason: str  # "travel" | "override" | "schedule" | "default"
    until: datetime | None = None  # schedule rule end, or override expiry hint


def resolve_city(conn, now: datetime | None = None) -> CityInfo:
    """Return the active city, considering travel, override, schedule, default."""
    if now is None:
        now = datetime.now()

    registry = load_registry()
    default_name = city_state.get_default_city(conn)
    if default_name not in registry:
        default_name = DEFAULT_CITY_NAME
    default_city = registry[default_name]

    # Travel mode wins completely: no city resolution runs, weather and
    # prayer nudges are suppressed by the callers as before.  The default
    # city stands in for any coordinate needs.
    travel = conn.execute("SELECT value FROM meta WHERE key = 'travel_mode'").fetchone()
    if travel is not None and travel["value"] == "1":
        return _info(default_city, "travel")

    override = city_state.get_state(conn)
    if override["override_mode"] is not None:
        until_ts = override["override_until"]
        if until_ts is not None and now.timestamp() >= until_ts:
            pass  # expired: fall through to schedule/default, nothing lingers
        else:
            name = override["override_city"] or default_name
            if name in registry:
                until = datetime.fromtimestamp(until_ts) if until_ts is not None else None
                return _info(registry[name], "override", until)

    rules = list_rules(conn)
    weekday = iranian_weekday(now.date())
    minute = now.hour * 60 + now.minute
    rule = active_rule(rules, weekday, minute)
    if rule is not None and rule.city in registry:
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        until = midnight + timedelta(minutes=min(rule.to_min, MINUTES_PER_DAY))
        return _info(registry[rule.city], "schedule", until)

    return _info(default_city, "default")


def _info(city: City, reason: str, until: datetime | None = None) -> CityInfo:
    return CityInfo(city.name, city.lat, city.lon, city.tz, city.weather_url, reason, until)
