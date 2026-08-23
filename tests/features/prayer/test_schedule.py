from datetime import datetime

import pytest

from dailydriver.features.prayer import schedule


class FrozenDateTime(datetime):
    current = datetime(2026, 8, 23, 0, 0)

    @classmethod
    def now(cls, tz=None):
        return cls.current


@pytest.mark.parametrize(
    ("hour", "expected"),
    [(4, "fajr"), (5, "fajr"), (12, "dhuhr_asr"), (19, "maghrib_isha")],
)
def test_current_slot_uses_prayer_boundaries(monkeypatch, hour, expected):
    FrozenDateTime.current = datetime(2026, 8, 23, hour)
    monkeypatch.setattr(schedule, "datetime", FrozenDateTime)
    monkeypatch.setattr(
        schedule,
        "get_approximate_times",
        lambda month, day: {"fajr": (5, 0), "dhuhr": (12, 0), "maghrib": (18, 0)},
    )
    assert schedule.current_slot() == expected


def test_prayer_slots_have_stable_database_names():
    assert schedule.PRAYER_SLOTS == ["fajr", "dhuhr_asr", "maghrib_isha"]
