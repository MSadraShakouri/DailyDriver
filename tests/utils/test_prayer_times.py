import math
from datetime import date, timedelta

import jdatetime
import pytest

from dailydriver.utils.prayer_times import (
    TEHRAN_LATITUDE,
    TEHRAN_LONGITUDE,
    TEHRAN_TIMEZONE,
    _julian_date,
    _sun_position,
    get_approximate_times,
    get_window_times,
)


def test_tehran_coordinates_match_published_1405_examples():
    # These minute-level values agree with the published Tehran 1405
    # Shahrivar table at the dates where the two methods were compared.
    assert get_approximate_times(6, 1, 1405) == {
        "fajr": (4, 0),
        "dhuhr": (12, 7),
        "maghrib": (19, 3),
    }
    assert get_approximate_times(6, 28, 1405) == {
        "fajr": (4, 26),
        "dhuhr": (11, 58),
        "maghrib": (18, 24),
    }


def test_year_is_part_of_the_calculation():
    # The solar curve is almost the same from one year to the next, but the
    # date must still be converted with the requested year rather than always
    # using today's year.  The difference is intentionally only about a minute.
    assert get_approximate_times(6, 28, 1402) == {
        "fajr": (4, 25),
        "dhuhr": (11, 58),
        "maghrib": (18, 25),
    }
    assert get_approximate_times(6, 28, 1405) != get_approximate_times(6, 28, 1402)


@pytest.mark.parametrize("month", range(1, 13))
def test_every_month_returns_plausible_ordered_times(month):
    times = get_approximate_times(month, 1, 1405)
    assert 3 <= times["fajr"][0] <= 6
    assert 11 <= times["dhuhr"][0] <= 13
    assert 17 <= times["maghrib"][0] <= 21
    assert times["fajr"] < times["dhuhr"] < times["maghrib"]


def test_invalid_jalali_date_is_rejected():
    with pytest.raises(ValueError):
        get_approximate_times(12, 30, 1405)


# ---------------------------------------------------------------------------
# Window boundaries (sunrise/sunset, fadilat ends, shar'i midnight)
# ---------------------------------------------------------------------------
# The city vectors below were validated against Iranian published tables
# (tala.ir and mavaqeet/azangoo to the second, pishkhanak.com to the minute,
# all declaring the University of Tehran Geophysics convention: Fajr 17.7,
# Maghrib 4.5) for Mehr 1, 1405 = 2026-09-23.  jdatetime.date(1405, 7, 1)
# is pinned instead of a literal to document the correspondence.

MEHR_1_1405 = jdatetime.date(1405, 7, 1).togregorian()


def test_window_times_agree_with_published_tehran_tables():
    # The three adhan times of the richer window calculation must match the
    # published Shahrivar values already pinned for get_approximate_times.
    shahrivar_1 = jdatetime.date(1405, 6, 1).togregorian()
    times = get_window_times(shahrivar_1)
    assert times["fajr"] == (4, 0)
    assert times["dhuhr"] == (12, 7)
    assert times["maghrib"] == (19, 3)


def test_window_times_match_iranian_city_tables():
    # Mehr 1, 1405 (2026-09-23).  Sources: tala.ir / mavaqeet.com (seconds,
    # University of Tehran formula) and pishkhanak.com (minutes, explicit
    # 17.7/4.5 statement).  All three cities agree to <= 30 seconds.
    karaj = get_window_times(MEHR_1_1405, 35.8327, 50.9916, 3.5)
    assert karaj["fajr"] == (4, 31)
    assert karaj["isfar_end"] == (4, 49)
    assert karaj["sunrise"] == (5, 55)
    assert karaj["dhuhr"] == (11, 58)
    assert karaj["dhuhr_fadilat_end"] == (15, 25)
    assert karaj["sunset"] == (18, 2)
    assert karaj["maghrib"] == (18, 20)
    assert karaj["shafaq_end"] == (19, 7)
    assert karaj["midnight"] == (23, 17)

    qom = get_window_times(MEHR_1_1405, 34.64, 50.8764, 3.5)
    assert qom["fajr"] == (4, 32)
    assert qom["sunrise"] == (5, 55)
    assert qom["dhuhr"] == (11, 59)
    assert qom["dhuhr_fadilat_end"] == (15, 26)
    assert qom["sunset"] == (18, 2)
    assert qom["maghrib"] == (18, 20)
    assert qom["midnight"] == (23, 18)

    mashhad = get_window_times(MEHR_1_1405, 36.2981, 59.6057, 3.5)
    assert mashhad["fajr"] == (3, 55)
    assert mashhad["sunrise"] == (5, 20)
    assert mashhad["dhuhr"] == (11, 24)
    assert mashhad["sunset"] == (17, 27)
    assert mashhad["maghrib"] == (17, 46)
    assert mashhad["shafaq_end"] == (18, 33)
    assert mashhad["midnight"] == (22, 42)


def test_fadilat_windows_match_published_durations():
    # hawzah.net publishes ~21 minutes for the Fajr fadilat window and the
    # marja offices 45-51 minutes for Maghrib; 14 degrees reproduces both at
    # Iranian latitudes.
    karaj = get_window_times(MEHR_1_1405, 35.8327, 50.9916, 3.5)
    minutes = lambda key: karaj[key][0] * 60 + karaj[key][1]
    assert 12 <= (minutes("isfar_end") - minutes("fajr")) % 1440 <= 30
    assert 40 <= (minutes("shafaq_end") - minutes("maghrib")) % 1440 <= 55
    # Dhuhr fadilat (shadow = 1 gnomon) is hours, not minutes, after zuwal.
    assert 150 <= (minutes("dhuhr_fadilat_end") - minutes("dhuhr")) % 1440 <= 270


@pytest.mark.parametrize("month", range(1, 13))
def test_window_times_stay_ordered_across_the_year(month):
    times = get_window_times(jdatetime.date(1405, month, 1).togregorian())
    sequence = [times[key] for key in ("fajr", "isfar_end", "sunrise", "dhuhr", "dhuhr_fadilat_end", "sunset", "maghrib", "shafaq_end", "midnight")]
    assert sequence == sorted(sequence)
    # The shar'i midnight of any Iranian day falls before the next civil
    # midnight, so the whole chain belongs to the same calendar day.
    assert times["midnight"][0] < 24


def test_midnight_is_midpoint_between_sunset_and_next_fajr():
    karaj = get_window_times(MEHR_1_1405, 35.8327, 50.9916, 3.5)
    fajr_next = get_window_times(MEHR_1_1405 + timedelta(days=1), 35.8327, 50.9916, 3.5)["fajr"]
    minutes = lambda hm: hm[0] * 60 + hm[1]
    sunset = minutes(karaj["sunset"])
    gap = (minutes(fajr_next) - sunset) % 1440
    midpoint = (sunset + gap / 2.0) % 1440
    assert abs(minutes(karaj["midnight"]) - midpoint) <= 1.0


def test_dhuhr_fadilat_end_altitude_satisfies_shadow_formula():
    # Independent wiring check: at the returned dhuhr_fadilat_end the sun's
    # altitude must equal cot(h) = tan(|lat - decl|) + 1 solved for h.
    gdate = date(2026, 3, 20)
    times = get_window_times(gdate)
    minutes = lambda hm: hm[0] * 60 + hm[1]
    hour_angle_deg = (minutes(times["dhuhr_fadilat_end"]) - minutes(times["dhuhr"])) * (15.0 / 60.0)
    declination = _sun_position(_julian_date(gdate) - TEHRAN_LONGITUDE / (15.0 * 24.0) + 0.5)[0]
    sin_altitude = (
        math.sin(math.radians(TEHRAN_LATITUDE)) * math.sin(math.radians(declination))
        + math.cos(math.radians(TEHRAN_LATITUDE))
        * math.cos(math.radians(declination))
        * math.cos(math.radians(hour_angle_deg))
    )
    altitude = math.degrees(math.asin(sin_altitude))
    expected = math.degrees(math.atan(1.0 / (math.tan(math.radians(abs(TEHRAN_LATITUDE - declination))) + 1.0)))
    assert abs(altitude - expected) < 0.1


def test_higher_latitude_lengthens_the_dhuhr_fadilat_window():
    gdate = date(2026, 6, 21)
    minutes_after_dhuhr = lambda lat: (
        lambda t: (t["dhuhr_fadilat_end"][0] * 60 + t["dhuhr_fadilat_end"][1])
        - (t["dhuhr"][0] * 60 + t["dhuhr"][1])
    )(get_window_times(gdate, lat, 51.0, 3.5))
    assert minutes_after_dhuhr(40.0) > minutes_after_dhuhr(25.0)


def test_window_times_default_to_tehran():
    explicit = get_window_times(MEHR_1_1405, TEHRAN_LATITUDE, TEHRAN_LONGITUDE, TEHRAN_TIMEZONE)
    assert get_window_times(MEHR_1_1405) == explicit


def test_approximate_times_keep_their_three_key_contract():
    assert set(get_approximate_times(7, 1, 1405)) == {"fajr", "dhuhr", "maghrib"}


def test_window_times_raise_when_sun_never_reaches_angle():
    # Polar day at 78N in June: sunset never happens.
    with pytest.raises(ValueError):
        get_window_times(date(2026, 6, 21), latitude=78.0, longitude=15.0, timezone=1.0)

