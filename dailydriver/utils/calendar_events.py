# dailydriver/utils/calendar_events.py
"""
Fetches and caches official Persian calendar events from the Persian Calendar project.
Offline‑first: uses a local JSON file, refreshing once a week.
"""
import json
import os
import time
import urllib.request

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
EVENTS_JSON = os.path.join(PROJECT_ROOT, "data", "events.json")
LAST_FETCH_FILE = os.path.join(PROJECT_ROOT, "data", ".events_last_fetch")
FETCH_URL = ("https://raw.githubusercontent.com/persian-calendar/persian-calendar/"
             "main/PersianCalendar/data/events.json")
CACHE_DAYS = 7

def _load_events():
    """Load events from the cached JSON file. Returns a list of event dicts."""
    with open(EVENTS_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)
    # data structure: {"Persian Calendar": [ ... ]}
    all_events = data.get("Persian Calendar", [])
    # Keep only Iran and International (جهانی)
    filtered = [e for e in all_events if e.get("type") in ("Iran", "International")]
    # Convert day/month to int (they are sometimes strings)
    for e in filtered:
        e["month"] = int(e["month"])
        e["day"] = int(e["day"])
    return filtered

def _fetch_and_cache():
    """Download the events JSON, save it, and return the filtered events."""
    req = urllib.request.Request(FETCH_URL, headers={"User-Agent": "DailyDriver/2.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw = resp.read()
    # Write raw JSON to disk
    os.makedirs(os.path.dirname(EVENTS_JSON), exist_ok=True)
    with open(EVENTS_JSON, "wb") as f:
        f.write(raw)
    # Save fetch timestamp
    with open(LAST_FETCH_FILE, "w") as f:
        f.write(str(int(time.time())))
    # Reload and return filtered events
    return _load_events()

def get_events() -> list | None:
    """
    Return a list of event dicts for the current year.
    Each dict has keys 'month', 'day', 'title', 'holiday'.
    Returns None if no cached file and network unavailable.
    """
    # Check if cache exists and is fresh
    if os.path.exists(EVENTS_JSON):
        if os.path.exists(LAST_FETCH_FILE):
            with open(LAST_FETCH_FILE) as f:
                last = int(f.read().strip())
            if time.time() - last < CACHE_DAYS * 86400:
                return _load_events()
        # Cache exists but too old -> try to refresh
        try:
            return _fetch_and_cache()
        except Exception:
            # Network failed, fall back to cached version
            return _load_events()
    # No cache at all -> try to fetch
    try:
        return _fetch_and_cache()
    except Exception:
        # No network, no cache :(
        return None

def get_todays_events(events: list | None):
    """Return a list of events happening today (if any)."""
    if not events:
        return []
    import jdatetime
    today = jdatetime.date.today()
    return [e for e in events if e["month"] == today.month and e["day"] == today.day]

def get_upcoming_events(events: list | None, days: int = 15):
    """
    Return events for the next `days` days.
    Returns a list of (jdatetime.date, event_dict) sorted by date.
    """
    if not events:
        return []
    import jdatetime
    today = jdatetime.date.today()
    result = []
    for d in range(days):
        date = today + jdatetime.timedelta(days=d)
        month, day = date.month, date.day
        for e in events:
            if e["month"] == month and e["day"] == day:
                result.append((date, e))
    return result
