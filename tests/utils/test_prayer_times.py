import pytest

from dailydriver.utils.prayer_times import get_approximate_times


def test_known_boundary_values():
    assert get_approximate_times(1, 1) == {
        "fajr": (4, 42),
        "dhuhr": (12, 12),
        "maghrib": (18, 36),
    }
    assert get_approximate_times(1, 22)["fajr"] == (4, 9)


def test_midpoint_is_interpolated_between_samples():
    fajr = get_approximate_times(1, 12)["fajr"]
    assert 265 <= fajr[0] * 60 + fajr[1] <= 275


@pytest.mark.parametrize("month", range(1, 13))
def test_every_month_returns_plausible_ordered_times(month):
    times = get_approximate_times(month, 1)
    assert 3 <= times["fajr"][0] <= 6
    assert 11 <= times["dhuhr"][0] <= 13
    assert 17 <= times["maghrib"][0] <= 21
    assert times["fajr"] < times["dhuhr"] < times["maghrib"]
