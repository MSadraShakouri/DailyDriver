from datetime import datetime

from dailydriver.features.prayer import schedule
from dailydriver.features.prayer.windows import SlotWindow


def _window(opens):
    base = datetime(2026, 8, 23)
    at = lambda hm: base.replace(hour=hm[0], minute=hm[1])
    return SlotWindow(opens=at(opens), green_until=at(opens), red_from=at(opens), deadline=at(opens))


def _fixed_windows():
    return {
        "fajr": _window((5, 0)),
        "dhuhr_asr": _window((12, 0)),
        "maghrib_isha": _window((18, 30)),
    }


def test_current_slot_uses_prayer_boundaries(monkeypatch):
    monkeypatch.setattr(schedule, "get_slot_windows", lambda *args, **kwargs: _fixed_windows())
    cases = [
        (datetime(2026, 8, 23, 4), "fajr"),
        (datetime(2026, 8, 23, 5), "fajr"),
        (datetime(2026, 8, 23, 12), "dhuhr_asr"),
        (datetime(2026, 8, 23, 19), "maghrib_isha"),
    ]
    for now, expected in cases:
        assert schedule.current_slot(now) == expected


def test_prayer_slots_have_stable_database_names():
    assert schedule.PRAYER_SLOTS == ["fajr", "dhuhr_asr", "maghrib_isha"]
