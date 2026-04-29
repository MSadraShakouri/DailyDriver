# dailydriver/utils/calendar_events.py
"""
Reads official Persian calendar events from a local, manually maintained file.
The file `data/events.json` should be a JSON array of objects with keys:
    month (int), day (int), title (str), holiday (bool), type (str)
Expected types: 'Iran', 'International'
"""
import json
import os
import jdatetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
EVENTS_JSON = os.path.join(PROJECT_ROOT, "data", "events.json")

def get_events():
    """
    Return a list of event dicts for the current year, or None if the file is missing.
    """
    if not os.path.exists(EVENTS_JSON):
        return None
    with open(EVENTS_JSON, "r", encoding="utf-8") as f:
        events = json.load(f)
    # Ensure month/day are int
    for e in events:
        e["month"] = int(e["month"])
        e["day"] = int(e["day"])
    return events

def get_todays_events(events):
    """Return a list of events happening today (if any)."""
    if not events:
        return []
    today = jdatetime.date.today()
    return [e for e in events if e["month"] == today.month and e["day"] == today.day]

def get_upcoming_events(events, days=15):
    """
    Return a list of (jdatetime.date, event_dict) for the next `days` days.
    """
    if not events:
        return []
    today = jdatetime.date.today()
    result = []
    for d in range(days):
        date = today + jdatetime.timedelta(days=d)
        month, day = date.month, date.day
        for e in events:
            if e["month"] == month and e["day"] == day:
                result.append((date, e))
    return result
