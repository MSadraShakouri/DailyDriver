"""Offline Tehran prayer-time calculation.

The old implementation kept four hand-entered points per Jalali month and
linearly interpolated between them.  That approximation is particularly poor
around the summer and winter turning points, and it was also tied to the
1403 calendar.

This module deliberately makes no network requests.  It keeps the location
and the Iranian calculation convention in the source and calculates the
three times needed by the application from the Sun's position.  The
calculation is the compact astronomical approximation used by PrayTimes.org,
with the University of Tehran parameters:

* Tehran: 35.689198 N, 51.388974 E
* civil time: UTC+03:30 (Iran currently has no DST)
* Fajr: Sun centre 17.7 degrees below the horizon
* Maghrib: Sun centre 4.5 degrees below the horizon

The formula is deterministic, fast, and works for any Gregorian/Jalali year;
there is no runtime fetch or generated-data file to become stale.  The
application only exposes minute precision, so the fractional result is
rounded once at the boundary of this module.

Formula lineage: the solar-position equations follow the open PrayTimes.org
algorithm (https://praytimes.org/).  Its LGPL attribution is retained here
rather than adding a runtime dependency.  The original algorithm is credited
to Hamid Zarrabi-Zadeh, Copyright (C) 2007-2010, under the GNU LGPL v3.0.
"""

from __future__ import annotations

import math
from datetime import date

import jdatetime

# Tehran coordinates used by the University of Tehran method pages we checked.
TEHRAN_LATITUDE = 35.689198
TEHRAN_LONGITUDE = 51.388974
TEHRAN_TIMEZONE = 3.5

# University of Tehran / Tehran calculation convention.  Angles are expressed
# as positive degrees below the horizon; the calculation turns them into the
# corresponding negative solar altitude internally.
FAJR_ANGLE = 17.7
MAGHRIB_ANGLE = 4.5

_DEG_TO_RAD = math.pi / 180.0


def _fix_angle(value: float) -> float:
    return value - 360.0 * math.floor(value / 360.0)


def _fix_hour(value: float) -> float:
    value -= 24.0 * math.floor(value / 24.0)
    return value if value >= 0 else value + 24.0


def _julian_date(gregorian_date: date) -> float:
    """Return the Julian day at midnight for a Gregorian date."""
    year = gregorian_date.year
    month = gregorian_date.month
    day = gregorian_date.day
    if month <= 2:
        year -= 1
        month += 12
    century = math.floor(year / 100.0)
    correction = 2 - century + math.floor(century / 4.0)
    return math.floor(365.25 * (year + 4716)) + math.floor(30.6001 * (month + 1)) + day + correction - 1524.5


def _sun_position(julian_day: float) -> tuple[float, float]:
    """Return (declination, equation_of_time_hours) for a Julian day."""
    days = julian_day - 2451545.0
    mean_anomaly = _fix_angle(357.529 + 0.98560028 * days)
    mean_longitude = _fix_angle(280.459 + 0.98564736 * days)
    ecliptic_longitude = _fix_angle(
        mean_longitude
        + 1.915 * math.sin(_DEG_TO_RAD * mean_anomaly)
        + 0.020 * math.sin(_DEG_TO_RAD * 2.0 * mean_anomaly)
    )
    obliquity = 23.439 - 0.00000036 * days

    declination = (
        math.asin(math.sin(_DEG_TO_RAD * obliquity) * math.sin(_DEG_TO_RAD * ecliptic_longitude)) / _DEG_TO_RAD
    )
    right_ascension = (
        math.atan2(
            math.cos(_DEG_TO_RAD * obliquity) * math.sin(_DEG_TO_RAD * ecliptic_longitude),
            math.cos(_DEG_TO_RAD * ecliptic_longitude),
        )
        / _DEG_TO_RAD
        / 15.0
    )
    right_ascension = _fix_hour(right_ascension)
    equation_of_time = mean_longitude / 15.0 - right_ascension
    return declination, equation_of_time


def _midday(julian_day: float, day_fraction: float) -> float:
    equation_of_time = _sun_position(julian_day + day_fraction)[1]
    return _fix_hour(12.0 - equation_of_time)


def _sun_angle_time(
    julian_day: float,
    latitude: float,
    angle_below_horizon: float,
    day_fraction: float,
    evening: bool,
) -> float:
    """Return local *solar* hours for a given twilight angle."""
    declination = _sun_position(julian_day + day_fraction)[0]
    noon = _midday(julian_day, day_fraction)
    numerator = -math.sin(_DEG_TO_RAD * angle_below_horizon) - math.sin(_DEG_TO_RAD * declination) * math.sin(
        _DEG_TO_RAD * latitude
    )
    denominator = math.cos(_DEG_TO_RAD * declination) * math.cos(_DEG_TO_RAD * latitude)
    cosine_hour_angle = numerator / denominator

    # Tehran is nowhere near a polar edge case.  Clamping still makes this
    # helper safe if the constants are reused for another location later.
    if not -1.0 <= cosine_hour_angle <= 1.0:
        raise ValueError("Sun does not reach the requested angle on this date")
    hour_angle = math.degrees(math.acos(cosine_hour_angle)) / 15.0
    return noon + (hour_angle if evening else -hour_angle)


def _calculate_tehran_times(gregorian_date: date) -> dict[str, float]:
    """Return fractional local-clock hours for the supported prayer times."""
    # Longitude is folded into the Julian date in the same way as the
    # PrayTimes algorithm.  The final correction converts solar hours to
    # Tehran civil time.
    julian_day = _julian_date(gregorian_date) - TEHRAN_LONGITUDE / (15.0 * 24.0)
    longitude_correction = TEHRAN_TIMEZONE - TEHRAN_LONGITUDE / 15.0

    def local_time(angle: float, initial_hour: float, evening: bool) -> float:
        solar_hour = _sun_angle_time(
            julian_day,
            TEHRAN_LATITUDE,
            angle,
            initial_hour / 24.0,
            evening,
        )
        return _fix_hour(solar_hour + longitude_correction)

    # Dhuhr is apparent solar noon.  The initial values are only used to
    # evaluate the date's solar position; one iteration is enough for the
    # minute-level output used by DailyDriver.
    dhuhr = _fix_hour(_midday(julian_day, 12.0 / 24.0) + longitude_correction)
    return {
        "fajr": local_time(180.0 - FAJR_ANGLE, 5.0, evening=False),
        "dhuhr": dhuhr,
        "maghrib": local_time(MAGHRIB_ANGLE, 18.0, evening=True),
    }


def _round_clock_hour(hours: float) -> tuple[int, int]:
    """Round fractional local hours to the minute shown by the application."""
    total_minutes = int(math.floor(hours * 60.0 + 0.5)) % (24 * 60)
    return total_minutes // 60, total_minutes % 60


def get_approximate_times(jalali_month: int, day: int, jalali_year: int | None = None):
    """Return Tehran Fajr, Dhuhr, and Maghrib as ``(hour, minute)`` tuples.

    ``jalali_year`` is optional for compatibility with the original helper.
    When omitted, the current Jalali year is used.  Callers dealing with a
    historical date should pass its year so leap-day and year-boundary
    conversions use the requested date rather than today's year.
    """
    if jalali_year is None:
        jalali_year = jdatetime.date.today().year
    try:
        jalali_date = jdatetime.date(jalali_year, jalali_month, day)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid Jalali date") from exc

    calculated = _calculate_tehran_times(jalali_date.togregorian())
    return {name: _round_clock_hour(hours) for name, hours in calculated.items()}


def get_times_for_jalali_date(jalali_date: jdatetime.date) -> dict[str, tuple[int, int]]:
    """Convenience wrapper for callers that already have a Jalali date."""
    return get_approximate_times(jalali_date.month, jalali_date.day, jalali_date.year)
