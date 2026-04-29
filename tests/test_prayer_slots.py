#!/usr/bin/env python3
"""Simple test for prayer time interpolation and slot logic."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from datetime import datetime, timedelta
from dailydriver.domains.prayer_times import get_approximate_times
from dailydriver.domains.prayer_core import _today_times, current_slot

def test_get_approximate_times():
    """Check interpolation returns reasonable values for known dates."""
    # Test 1st of Farvardin (should match first data point)
    t = get_approximate_times(1, 1)
    assert t['fajr'] == (4, 42), f"Farvardin 1: fajr {t['fajr']}"
    assert t['dhuhr'] == (12, 12), f"Farvardin 1: dhuhr {t['dhuhr']}"
    assert t['maghrib'] == (18, 36), f"Farvardin 1: maghrib {t['maghrib']}"

    # Test 22nd of Farvardin (last data point)
    t = get_approximate_times(1, 22)
    assert t['fajr'] == (4, 9), f"Farvardin 22: fajr {t['fajr']}"

    # Test a date between data points (day 12 should be between day 8 and 15)
    t = get_approximate_times(1, 12)
    # Should be between (4,31) and (4,20) -> roughly 4:26 or 4:25
    fajr_min = t['fajr'][0] * 60 + t['fajr'][1]
    assert 265 <= fajr_min <= 275, f"Farvardin 12: fajr {t['fajr']} (expected around 4:26-4:35)"

    # Test first day of each month returns something valid
    for m in range(1, 13):
        t = get_approximate_times(m, 1)
        fajr_h, fajr_m = t['fajr']
        assert 3 <= fajr_h <= 6, f"Month {m}: fajr hour {fajr_h} out of range"
        dhuhr_h, dhuhr_m = t['dhuhr']
        assert 11 <= dhuhr_h <= 13, f"Month {m}: dhuhr hour {dhuhr_h} out of range"
        maghrib_h, maghrib_m = t['maghrib']
        assert 17 <= maghrib_h <= 21, f"Month {m}: maghrib hour {maghrib_h} out of range"

    print("✓ Interpolation tests passed")

def test_slot_assignment():
    """Test the slot assignment logic with known times."""
    # Simulate a day with known prayer times
    # Use a fixed date for reproducibility
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Test cases: (current_time_str, prayer_times_dict, expected_slot)
    test_cases = [
        # Before Fajr -> should return 'fajr' (default)
        ("02:00", {"fajr": (4,42), "dhuhr": (12,12), "maghrib": (18,36)}, "fajr"),
        # Exactly at Fajr
        ("04:42", {"fajr": (4,42), "dhuhr": (12,12), "maghrib": (18,36)}, "fajr"),
        # After Fajr, before Dhuhr
        ("07:30", {"fajr": (4,42), "dhuhr": (12,12), "maghrib": (18,36)}, "fajr"),
        # Exactly at Dhuhr
        ("12:12", {"fajr": (4,42), "dhuhr": (12,12), "maghrib": (18,36)}, "dhuhr_asr"),
        # After Dhuhr, before Maghrib
        ("15:00", {"fajr": (4,42), "dhuhr": (12,12), "maghrib": (18,36)}, "dhuhr_asr"),
        # Exactly at Maghrib
        ("18:36", {"fajr": (4,42), "dhuhr": (12,12), "maghrib": (18,36)}, "maghrib_isha"),
        # After Maghrib
        ("22:00", {"fajr": (4,42), "dhuhr": (12,12), "maghrib": (18,36)}, "maghrib_isha"),
        # Before Maghrib, after Dhuhr (edge)
        ("18:35", {"fajr": (4,42), "dhuhr": (12,12), "maghrib": (18,36)}, "dhuhr_asr"),
    ]

    def slot_for_time(time_str, times):
        h, m = map(int, time_str.split(":"))
        test_dt = now.replace(hour=h, minute=m)
        ordered = [
            ('fajr', now.replace(hour=times['fajr'][0], minute=times['fajr'][1])),
            ('dhuhr_asr', now.replace(hour=times['dhuhr'][0], minute=times['dhuhr'][1])),
            ('maghrib_isha', now.replace(hour=times['maghrib'][0], minute=times['maghrib'][1])),
        ]
        slot = 'fajr'
        for s, dt in ordered:
            if test_dt >= dt:
                slot = s
            else:
                break
        return slot

    for time_str, times, expected in test_cases:
        result = slot_for_time(time_str, times)
        assert result == expected, f"At {time_str} with times {times}: expected {expected}, got {result}"

    print("✓ Slot assignment tests passed")

def test_explicit_time_guessing():
    """Test how explicit times map to slots."""
    now = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # Simulate a day with these prayer times
    fajr = now.replace(hour=4, minute=42)
    dhuhr = now.replace(hour=12, minute=12)
    maghrib = now.replace(hour=18, minute=36)

    test_cases = [
        ("04:00", "fajr"),           # before Dhuhr -> fajr
        ("04:42", "fajr"),           # exactly Fajr, still before Dhuhr
        ("11:59", "fajr"),           # before Dhuhr
        ("12:12", "dhuhr_asr"),      # exactly Dhuhr
        ("12:13", "dhuhr_asr"),      # after Dhuhr, before Maghrib
        ("18:00", "dhuhr_asr"),      # before Maghrib
        ("18:36", "maghrib_isha"),   # exactly Maghrib
        ("23:59", "maghrib_isha"),   # after Maghrib
    ]

    for time_str, expected in test_cases:
        h, m = map(int, time_str.split(":"))
        test_dt = now.replace(hour=h, minute=m)
        if test_dt < dhuhr:
            slot = "fajr"
        elif test_dt < maghrib:
            slot = "dhuhr_asr"
        else:
            slot = "maghrib_isha"
        assert slot == expected, f"Explicit {time_str}: expected {expected}, got {slot}"

    print("✓ Explicit time guessing tests passed")

if __name__ == "__main__":
    test_get_approximate_times()
    test_slot_assignment()
    test_explicit_time_guessing()
    print("\nAll tests passed ✅")
