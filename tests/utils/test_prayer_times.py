import pytest

from dailydriver.utils.prayer_times import get_approximate_times


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
