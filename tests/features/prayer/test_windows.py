"""Invariant checks over the computed slot windows.

The bands are always computed from (lat, lon, tz, date) — never hardcoded —
so the suite sweeps representative dates (equinoxes, both solstices) for the
shipped registry cities and asserts every window is well-formed:

    opens < green_until < red_from < deadline

A zero or negative band would signal a criteria mismatch (e.g. a green
boundary that never gets reached at that latitude), not a legitimate
"no yellow today" case.
"""

from datetime import date

import pytest

from dailydriver.core.location.registry import load_registry
from dailydriver.features.prayer.windows import get_slot_windows

# Equinoxes and both solstices bracket the seasonal extremes.
SAMPLE_DATES = (
    date(2026, 3, 20),  # spring equinox
    date(2026, 6, 21),  # summer solstice
    date(2026, 9, 23),  # autumn equinox
    date(2026, 12, 21),  # winter solstice (deepest solar noon for Tehran)
    date(2027, 3, 20),  # next spring equinox
)


@pytest.mark.parametrize("city_name", ("Tehran", "Karaj", "Qom", "Mashhad"))
def test_every_band_is_positive_and_ordered(city_name):
    city = load_registry()[city_name]
    for day in SAMPLE_DATES:
        for slot, window in get_slot_windows(day, city.lat, city.lon, city.tz).items():
            assert window.opens < window.green_until, (city_name, slot, day, "green band empty")
            assert window.green_until < window.red_from, (city_name, slot, day, "yellow band empty")
            assert window.red_from < window.deadline, (city_name, slot, day, "red band empty")


@pytest.mark.parametrize("city_name", ("Tehran", "Karaj", "Qom", "Mashhad"))
def test_red_stretch_matches_the_locked_durations(city_name):
    from dailydriver.features.prayer.windows import RED_MINUTES

    city = load_registry()[city_name]
    for day in SAMPLE_DATES:
        for slot, window in get_slot_windows(day, city.lat, city.lon, city.tz).items():
            minutes = (window.deadline - window.red_from).total_seconds() / 60
            assert minutes == RED_MINUTES[slot], (city_name, slot, day)


def test_midnight_uses_the_next_fajr_convention():
    # Shar'i midnight sits between sunset and the NEXT day's fajr adhan.
    city = load_registry()["Tehran"]
    window = get_slot_windows(date(2026, 9, 23), city.lat, city.lon, city.tz)["maghrib_isha"]
    assert window.opens.date() == window.deadline.date()  # same-day deadline sanity
    hours = (window.deadline - window.opens).total_seconds() / 3600
    assert hours == pytest.approx(4.95, abs=0.2)
