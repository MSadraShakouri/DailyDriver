"""
Dynamic calendar events from three calendar systems (Jalali, Gregorian, Hijri).
Stores events in separate JSON files under data/.
Converts all events to the current Jalali date using jdatetime and hijridate.
"""

import json
import os
from datetime import date, timedelta

import jdatetime
from hijridate import Gregorian as HijriGregorian  # avoid name clash
from hijridate import Hijri

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

JALALI_FILE = os.path.join(DATA_DIR, "events_jalali.json")
GREGORIAN_FILE = os.path.join(DATA_DIR, "events_gregorian.json")
HIJRI_FILE = os.path.join(DATA_DIR, "events_hijri.json")

# Cache: list of (jalali_date, event_dict) after conversion
_cached_events = None
_cache_year = None


def _load_json(filepath):
    if not os.path.exists(filepath):
        return []
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _gregorian_to_jalali(gdate):
    """Convert Gregorian date (datetime.date) to Jalali date (jdatetime.date)."""
    return jdatetime.date.fromgregorian(date=gdate)


def _jalali_to_gregorian(jdate):
    """Convert Jalali date to Gregorian."""
    return jdate.togregorian()


def _hijri_to_gregorian(hijri_year, hijri_month, hijri_day):
    """Convert Hijri date to Gregorian using hijridate (Umm al-Qura)."""
    h = Hijri(hijri_year, hijri_month, hijri_day)
    return h.to_gregorian()  # returns datetime.date


def _gregorian_to_hijri(gdate):
    """Convert Gregorian date to Hijri (returns Hijri object)."""
    return HijriGregorian.fromdate(gdate).to_hijri()


def _get_hijri_year_for_jalali_year(jalali_year):
    """Return the most likely Hijri year(s) that overlap with the given Jalali year.
    Returns a list of two years (current and next)."""
    # Find first day of Jalali year in Gregorian
    first_day_jalali = jdatetime.date(jalali_year, 1, 1)
    first_day_greg = first_day_jalali.togregorian()
    # Get corresponding Hijri year
    hijri_start = _gregorian_to_hijri(first_day_greg)
    cur_hijri_year = hijri_start.year
    # Also next Hijri year may cover later part of Jalali year
    return [cur_hijri_year, cur_hijri_year + 1]


from .hijri import get_hijri_offset


def _convert_all_events(target_jalali_year):
    """
    Load and convert events from all three calendar files to Jalali dates
    within the given Jalali year (or the nearest occurrence).
    Returns a list of (jalali_date, event_info) sorted by date.
    """
    events = []

    # 1. Jalali events (just read month/day and create date in target year)
    for je in _load_json(JALALI_FILE):
        try:
            m, d = je["month"], je["day"]
            jdate = jdatetime.date(target_jalali_year, m, d)
            events.append((jdate, je))
        except ValueError:
            continue

    # 2. Gregorian events (recurring; map to Jalali via the year's Gregorian equivalents)
    # We'll use the Gregorian year that corresponds to most of the Jalali year.
    # For simplicity, take the Gregorian year of the first day of the Jalali year.
    first_day_greg = jdatetime.date(target_jalali_year, 1, 1).togregorian()
    gregorian_year = first_day_greg.year
    for ge in _load_json(GREGORIAN_FILE):
        try:
            m, d = ge["month"], ge["day"]
            gdate = date(gregorian_year, m, d)
            jdate = _gregorian_to_jalali(gdate)
            events.append((jdate, ge))
        except ValueError:
            continue

    # 3. Hijri events
    # We need to find the Hijri year(s) that overlap with the Jalali year.
    hijri_years = _get_hijri_year_for_jalali_year(target_jalali_year)
    for he in _load_json(HIJRI_FILE):
        m, d = he["month"], he["day"]
        # Try both Hijri years, keep the one that falls within the Jalali year or
        # within a reasonable range (e.g., the next few months) for the upcoming 15 days.
        # For simplicity, we'll try both and keep the earliest that is >= first day of Jalali year.
        possible = []
        for hy in hijri_years:
            try:
                gdate = _hijri_to_gregorian(hy, m, d)
                offset = get_hijri_offset()
                if offset:
                    gdate = gdate - timedelta(days=offset)
                jdate = _gregorian_to_jalali(gdate)
                if jdate.year == target_jalali_year or jdate.year == target_jalali_year + 1:
                    possible.append(jdate)
            except ValueError:
                pass
        if possible:
            # Choose the earliest occurrence
            jdate = min(possible)
            events.append((jdate, he))

    # Remove duplicates (same event title on same date)
    seen = set()
    unique = []
    for jdate, ev in sorted(events, key=lambda x: x[0]):
        key = (jdate, ev["title_en"])
        if key not in seen:
            seen.add(key)
            unique.append((jdate, ev))
    return unique


def invalidate_cache():
    """Discard converted event data after calendar configuration changes."""
    global _cached_events, _cache_year
    _cached_events = None
    _cache_year = None


def _refresh_cache():
    """Update cached events for the current Jalali year."""
    global _cached_events, _cache_year
    today = jdatetime.date.today()
    current_year = today.year
    # Also preload next year's events if we're near the end of the year
    # For simplicity, just load current year; upcoming events will handle boundary.
    _cached_events = _convert_all_events(current_year)
    _cache_year = current_year


def get_events():
    """Return a list of (jalali_date, event_dict) for the current year."""
    global _cached_events
    if _cached_events is None or _cache_year != jdatetime.date.today().year:
        _refresh_cache()
    return _cached_events


def get_todays_events(events=None):
    """Return events happening today (as Jalali date)."""
    if events is None:
        events = get_events()
    if events is None:
        return []
    today = jdatetime.date.today()
    return [ev for d, ev in events if d == today]


def get_upcoming_events(events=None, days=15):
    """Return list of (jalali_date, event_dict) for the next `days` days."""
    if events is None:
        events = get_events()
    if events is None:
        return []
    today = jdatetime.date.today()
    end = today + jdatetime.timedelta(days=days)
    upcoming = []
    for d, ev in events:
        if today <= d <= end:
            upcoming.append((d, ev))
    upcoming.sort(key=lambda x: x[0])
    return upcoming


def get_events_for_date(jalali_date):
    """Return list of event dicts for a specific Jalali date."""
    all_events = get_events()
    if all_events is None:
        return []
    return [ev for d, ev in all_events if d == jalali_date]
