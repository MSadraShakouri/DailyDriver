"""Prayer slot windows derived from the solar boundary times.

Each merged slot opens at its adhan and runs to a fixed shar'i deadline
(Khamenei's risala):

* Fajr: adhan -> sunrise
* Dhuhr & Asr: adhan -> sunset
* Maghrib & Isha: adhan -> shar'i midnight

Merged slots stay merged, and only the first prayer of a merged slot drives
the green state: green ends at that prayer's fadilat boundary, yellow fills
the gap, and red covers the final stretch before the deadline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta

from dailydriver.utils.prayer_times import (
    TEHRAN_LATITUDE,
    TEHRAN_LONGITUDE,
    TEHRAN_TIMEZONE,
    get_window_times,
)

# Red state begins this many minutes before the window deadline.
RED_MINUTES = {
    "fajr": 30,
    "dhuhr_asr": 120,
    "maghrib_isha": 120,
}


@dataclass(frozen=True)
class SlotWindow:
    """One slot's window: opens -> green_until -> red_from -> deadline."""

    opens: datetime
    green_until: datetime
    red_from: datetime
    deadline: datetime


def get_slot_windows(
    gregorian_date: date,
    latitude: float | None = None,
    longitude: float | None = None,
    timezone: float | None = None,
) -> dict[str, SlotWindow]:
    """Return the three merged slot windows for a date (Tehran by default)."""
    times = get_window_times(gregorian_date, latitude, longitude, timezone)

    def at(key: str) -> datetime:
        hour, minute = times[key]
        return datetime(gregorian_date.year, gregorian_date.month, gregorian_date.day, hour, minute)

    return {
        "fajr": SlotWindow(
            opens=at("fajr"),
            green_until=at("isfar_end"),
            red_from=at("sunrise") - timedelta(minutes=RED_MINUTES["fajr"]),
            deadline=at("sunrise"),
        ),
        "dhuhr_asr": SlotWindow(
            opens=at("dhuhr"),
            green_until=at("dhuhr_fadilat_end"),
            red_from=at("sunset") - timedelta(minutes=RED_MINUTES["dhuhr_asr"]),
            deadline=at("sunset"),
        ),
        "maghrib_isha": SlotWindow(
            opens=at("maghrib"),
            green_until=at("shafaq_end"),
            red_from=at("midnight") - timedelta(minutes=RED_MINUTES["maghrib_isha"]),
            deadline=at("midnight"),
        ),
    }
