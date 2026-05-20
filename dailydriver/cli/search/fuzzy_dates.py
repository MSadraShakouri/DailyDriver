# dailydriver/cli/search/fuzzy_dates.py
"""Relative date, weekday, and month scoring with fuzzy token matching."""

from datetime import datetime, timedelta

import jdatetime
from hijridate import Gregorian as HijriGregorian

from .fuzzy_utils import fuzzy_match

# English weekday names (Monday=0 ... Sunday=6)
WEEKDAY_NAMES = [
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
]

# Jalali month names (lowercase)
JALALI_MONTHS = [
    "farvardin",
    "ordibehesht",
    "khordad",
    "tir",
    "mordad",
    "shahrivar",
    "mehr",
    "aban",
    "azar",
    "dey",
    "bahman",
    "esfand",
]

# Gregorian month names (lowercase)
GREGORIAN_MONTHS = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]

# Hijri month names (lowercase)
HIJRI_MONTHS = [
    "muharram",
    "safar",
    "rabi al-awwal",
    "rabi al-thani",
    "jumada al-ula",
    "jumada al-thani",
    "rajab",
    "shaban",
    "ramadan",
    "shawwal",
    "dhu al-qadah",
    "dhu al-hijjah",
]


def _days_away(entry_date: datetime, target_date: datetime) -> int:
    """Absolute day difference between two dates (ignoring time)."""
    return abs((entry_date.date() - target_date.date()).days)


def score_dates(entry_created_at_unix: int | None, query_tokens: list[str]) -> float:
    """Return a date‑related score for an entry.
    Handles relative phrases (yesterday, last week, etc.), weekdays, and month names.
    """
    if entry_created_at_unix is None:
        return 0.0

    entry_dt = datetime.fromtimestamp(entry_created_at_unix)
    now = datetime.now()
    score = 0.0

    # --- relative phrases ---
    relative_phrases = {
        "today": (now - timedelta(hours=48), now),  # today + yesterday
        "yesterday": (
            now - timedelta(days=3),
            now - timedelta(days=1),
        ),  # yesterday + 2 days ago
        "last week": (now - timedelta(days=10), now),
        "last month": (now - timedelta(days=40), now),
    }

    for token in query_tokens:
        if token in relative_phrases:
            start, end = relative_phrases[token]
            if start <= entry_dt <= end:
                # Entry is within window, give high score
                score += 1.0
            else:
                # Distance from window (approximate)
                dist = 0.0
                if entry_dt < start:
                    dist = (start - entry_dt).total_seconds() / 86400.0
                else:
                    dist = (entry_dt - end).total_seconds() / 86400.0
                score += max(0.0, 1.0 / (1 + dist))

    # --- weekdays ---
    for token in query_tokens:
        match = fuzzy_match(token, WEEKDAY_NAMES, max_dist=2)
        if match:
            target_weekday = WEEKDAY_NAMES.index(match)
            # Find the most recent occurrence of that weekday
            today = now.date()
            days_behind = (today.weekday() - target_weekday) % 7
            if days_behind == 0:
                days_behind = 7  # most recent past occurrence
            target_date = today - timedelta(days=days_behind)
            # Allow ±1 day
            days_diff = _days_away(
                entry_dt, datetime.combine(target_date, datetime.min.time())
            )
            if days_diff <= 1:
                score += 1.0 / (1 + days_diff)

    # --- months ---
    jalali_date = jdatetime.date.fromgregorian(date=entry_dt.date())
    gregorian_month = entry_dt.month
    hijri_date = HijriGregorian.fromdate(entry_dt.date()).to_hijri()
    hijri_month = hijri_date.month

    for token in query_tokens:
        # Jalali months
        match = fuzzy_match(token, JALALI_MONTHS, max_dist=2)
        if match:
            month_idx = JALALI_MONTHS.index(match) + 1
            diff = abs(jalali_date.month - month_idx)
            diff = min(diff, 12 - diff)
            if diff == 0:
                score += 1.0
            elif diff <= 1:  # ±1 month forgiveness
                score += 0.5
        # Gregorian months
        match = fuzzy_match(token, GREGORIAN_MONTHS, max_dist=2)
        if match:
            month_idx = GREGORIAN_MONTHS.index(match) + 1
            diff = abs(gregorian_month - month_idx)
            diff = min(diff, 12 - diff)
            if diff == 0:
                score += 1.0
            elif diff <= 1:
                score += 0.5
        # Hijri months
        match = fuzzy_match(token, HIJRI_MONTHS, max_dist=2)
        if match:
            month_idx = HIJRI_MONTHS.index(match) + 1
            diff = abs(hijri_month - month_idx)
            diff = min(diff, 12 - diff)
            if diff == 0:
                score += 1.0
            elif diff <= 1:
                score += 0.5

    return score
