"""Default-city and override persistence for the single ``city_state`` row.

An override is one concept: set a city until Y, where Y is ``next_change``,
a ``specific`` timestamp, or ``indefinite``.  ``override_city`` NULL with an
active mode means "suspend the schedule and use the default city";
``override_mode`` NULL means no override is active.
"""

from __future__ import annotations

from dailydriver.core.location.registry import DEFAULT_CITY_NAME

OVERRIDE_MODES = ("next_change", "specific", "indefinite")


def get_state(conn) -> dict:
    row = conn.execute(
        "SELECT default_city, override_city, override_until, override_mode FROM city_state WHERE id = 1"
    ).fetchone()
    if row is None:
        return {
            "default_city": DEFAULT_CITY_NAME,
            "override_city": None,
            "override_until": None,
            "override_mode": None,
        }
    return {
        "default_city": row["default_city"],
        "override_city": row["override_city"],
        "override_until": row["override_until"],
        "override_mode": row["override_mode"],
    }


def get_default_city(conn) -> str:
    return get_state(conn)["default_city"] or DEFAULT_CITY_NAME


def set_default_city(conn, name: str) -> None:
    conn.execute("UPDATE city_state SET default_city = ? WHERE id = 1", (name,))
    conn.commit()


def set_override(conn, city: str | None, until_ts: int | None, mode: str) -> None:
    """Set (or replace) the active override.  ``city=None`` selects the default."""
    if mode not in OVERRIDE_MODES:
        raise ValueError(f"Invalid override mode: {mode!r}")
    conn.execute(
        "UPDATE city_state SET override_city = ?, override_until = ?, override_mode = ? WHERE id = 1",
        (city, until_ts, mode),
    )
    conn.commit()


def clear_override(conn) -> None:
    conn.execute(
        "UPDATE city_state SET override_city = NULL, override_until = NULL, override_mode = NULL WHERE id = 1"
    )
    conn.commit()
