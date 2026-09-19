from datetime import date

from dailydriver.features.calendar.converter import (
    HijriDate,
    gregorian_to_hijri,
    hijri_to_gregorian,
)


def test_iranian_table_matches_the_four_announced_1448_boundaries():
    assert gregorian_to_hijri(date(2026, 6, 16)) == HijriDate(1448, 1, 1)
    assert gregorian_to_hijri(date(2026, 7, 16)) == HijriDate(1448, 2, 1)
    assert gregorian_to_hijri(date(2026, 8, 14)) == HijriDate(1448, 3, 1)
    assert gregorian_to_hijri(date(2026, 9, 13)) == HijriDate(1448, 4, 1)


def test_iranian_month_lengths_are_preserved_at_boundaries():
    assert gregorian_to_hijri(date(2026, 7, 15)) == HijriDate(1448, 1, 30)
    assert gregorian_to_hijri(date(2026, 8, 13)) == HijriDate(1448, 2, 29)
    assert gregorian_to_hijri(date(2026, 9, 12)) == HijriDate(1448, 3, 30)
    assert gregorian_to_hijri(date(2026, 10, 11)) == HijriDate(1448, 4, 29)


def test_iranian_month_start_round_trips():
    starts = {
        HijriDate(1448, 1, 1): date(2026, 6, 16),
        HijriDate(1448, 2, 1): date(2026, 7, 16),
        HijriDate(1448, 3, 1): date(2026, 8, 14),
        HijriDate(1448, 4, 1): date(2026, 9, 13),
        HijriDate(1448, 5, 1): date(2026, 10, 12),
    }
    for hijri, gregorian in starts.items():
        assert hijri_to_gregorian(hijri) == gregorian
        assert gregorian_to_hijri(gregorian) == hijri


def test_offset_sign_matches_existing_daily_driver_convention():
    # A negative offset shifts the source Gregorian date backwards, moving a
    # calculated month boundary one civil day later in the displayed calendar.
    assert gregorian_to_hijri(date(2026, 9, 13), offset=-1) == HijriDate(1448, 3, 30)
    assert hijri_to_gregorian(HijriDate(1448, 4, 1), offset=-1) == date(2026, 9, 14)


def test_calculated_fallback_remains_available_outside_iranian_table():
    assert gregorian_to_hijri(date(2077, 10, 18)) == HijriDate(1500, 12, 1)
    assert hijri_to_gregorian(HijriDate(1500, 12, 1)) == date(2077, 10, 18)
