"""Offline Gregorian/Hijri conversion with an Iranian-first calendar model.

The Iranian month-start table is the primary source for dates covered by it.
The bundled calculated table preserves the old ``hijridate``/Umm al-Qura
fallback without requiring a third-party runtime dependency.  Neither the
calculated fallback nor future Iranian table rows should be presented as a
live religious announcement.
"""

from __future__ import annotations

import json
from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
IRANIAN_DATA_FILE = PROJECT_ROOT / "data" / "hijri_iran.json"
CALCULATED_DATA_FILE = PROJECT_ROOT / "data" / "hijri_calculated_month_starts.json"

MONTH_NAMES = (
    "Muharram",
    "Safar",
    "Rabi al-Awwal",
    "Rabi al-Thani",
    "Jumada al-Ula",
    "Jumada al-Thani",
    "Rajab",
    "Sha'ban",
    "Ramadan",
    "Shawwal",
    "Dhu al-Qa'dah",
    "Dhu al-Hijjah",
)


@dataclass(frozen=True, order=True)
class HijriDate:
    """A validated lunar date returned by this module."""

    year: int
    month: int
    day: int

    def month_name(self) -> str:
        """Return the English name used by DailyDriver's previous converter."""
        return MONTH_NAMES[self.month - 1]

    def isoformat(self) -> str:
        return f"{self.year:04}-{self.month:02}-{self.day:02}"

    def __str__(self) -> str:
        return self.isoformat()


@dataclass(frozen=True)
class _MonthAnchor:
    year: int
    month: int
    start: date
    days: int


class _AnchorCalendar:
    """Conversion through an ordered table of month starts."""

    def __init__(self, entries: list[dict]) -> None:
        anchors: list[_MonthAnchor] = []
        for entry in entries:
            year, month = (int(part) for part in entry["hijri"].split("-"))
            anchors.append(
                _MonthAnchor(
                    year=year,
                    month=month,
                    start=date.fromisoformat(entry["start"]),
                    days=int(entry["days"]),
                )
            )

        if not anchors:
            raise ValueError("Hijri anchor table is empty")
        if anchors != sorted(anchors, key=lambda item: item.start):
            raise ValueError("Hijri anchor table is not ordered by Gregorian start")

        self._anchors = anchors
        self._starts = [anchor.start for anchor in anchors]
        self._by_hijri = {(anchor.year, anchor.month): anchor for anchor in anchors}

    @property
    def first_start(self) -> date:
        return self._anchors[0].start

    @property
    def last_end(self) -> date:
        anchor = self._anchors[-1]
        return anchor.start + timedelta(days=anchor.days - 1)

    def has_gregorian(self, value: date) -> bool:
        return self.first_start <= value <= self.last_end

    def has_hijri(self, value: HijriDate) -> bool:
        return (value.year, value.month) in self._by_hijri

    def from_gregorian(self, value: date) -> HijriDate:
        index = bisect_right(self._starts, value) - 1
        if index < 0:
            raise ValueError("Gregorian date is before this Hijri table")
        anchor = self._anchors[index]
        day = (value - anchor.start).days + 1
        if day > anchor.days:
            raise ValueError("Gregorian date is outside this Hijri table")
        return HijriDate(anchor.year, anchor.month, day)

    def to_gregorian(self, value: HijriDate) -> date:
        anchor = self._by_hijri.get((value.year, value.month))
        if anchor is None:
            raise ValueError("Hijri date is outside this Hijri table")
        if not 1 <= value.day <= anchor.days:
            raise ValueError(f"day must be in 1-{anchor.days} for month")
        return anchor.start + timedelta(days=value.day - 1)


def _load_calendar(path: Path) -> _AnchorCalendar:
    with path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return _AnchorCalendar(payload["months"])


# Loading once keeps the calendar conversion cheap while still making all data
# explicit and inspectable in data/*.json. Tests can replace these module values.
_iranian_calendar = _load_calendar(IRANIAN_DATA_FILE)
_calculated_calendar = _load_calendar(CALCULATED_DATA_FILE)


def _from_gregorian_raw(value: date) -> HijriDate:
    """Convert without an offset, preferring the Iranian table."""
    if _iranian_calendar.has_gregorian(value):
        return _iranian_calendar.from_gregorian(value)
    return _calculated_calendar.from_gregorian(value)


def _to_gregorian_raw(value: HijriDate) -> date:
    """Convert without an offset, preferring the Iranian table."""
    if _iranian_calendar.has_hijri(value):
        return _iranian_calendar.to_gregorian(value)
    return _calculated_calendar.to_gregorian(value)


def gregorian_to_hijri(value: date, offset: int = 0) -> HijriDate:
    """Convert Gregorian *value* to Iranian-first Hijri.

    ``offset`` retains DailyDriver's established sign convention: the input
    Gregorian date is shifted by the offset before conversion.  Therefore an
    offset of ``-1`` moves a calculated month boundary one civil day later.
    """
    return _from_gregorian_raw(value + timedelta(days=offset))


def hijri_to_gregorian(value: HijriDate, offset: int = 0) -> date:
    """Convert an Iranian-first Hijri date to Gregorian."""
    return _to_gregorian_raw(value) - timedelta(days=offset)


def _previous_or_next(value: HijriDate, delta: int) -> HijriDate:
    month_index = value.year * 12 + value.month - 1 + delta
    year, month_index = divmod(month_index, 12)
    return HijriDate(year, month_index + 1, 1)


def _raw_month_length(value: HijriDate) -> int:
    calendar = _iranian_calendar if _iranian_calendar.has_hijri(value) else _calculated_calendar
    return calendar._by_hijri[(value.year, value.month)].days


def gregorian_to_hijri_with_month_offsets(value: date, offset_for_month: Callable[[int, int], int]) -> HijriDate:
    """Convert using a potentially different correction for each Hijri month.

    A month correction moves that month's Gregorian start by the same amount
    as :func:`hijri_to_gregorian`.  Looking at nearby adjusted starts keeps
    Gregorian-to-Hijri conversion inverse-compatible with a corrected Hijri
    event, including when a positive correction moves a boundary earlier.
    """
    raw = _from_gregorian_raw(value)
    candidates = []
    for delta in range(-2, 3):
        candidate = _previous_or_next(raw, delta)
        try:
            start = _to_gregorian_raw(candidate) - timedelta(days=offset_for_month(candidate.year, candidate.month))
        except ValueError:
            continue
        if start <= value:
            candidates.append((start, candidate))

    if not candidates:
        raise ValueError("Gregorian date is before the adjusted Hijri table")

    start, candidate = max(candidates, key=lambda item: item[0])
    day = min((value - start).days + 1, _raw_month_length(candidate))
    return HijriDate(candidate.year, candidate.month, day)


def make_hijri_date(year: int, month: int, day: int) -> HijriDate:
    """Construct a Hijri date after validating it against the active tables."""
    value = HijriDate(year, month, day)
    _to_gregorian_raw(value)
    return value


def reset_calendar_caches_for_tests() -> None:
    """Reload tables after a test replaces the data paths or files."""
    global _iranian_calendar, _calculated_calendar
    _iranian_calendar = _load_calendar(IRANIAN_DATA_FILE)
    _calculated_calendar = _load_calendar(CALCULATED_DATA_FILE)
