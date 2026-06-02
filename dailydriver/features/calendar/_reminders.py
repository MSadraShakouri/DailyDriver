# dailydriver/utils/event_reminders.py
"""Calendar event reminders and tomorrow preview."""

import jdatetime

EVENT_SCHEDULE = {
    0: [],
    1: [14, 7, 3, 2, 1, 0],
    2: [28, 21, 14, 7, 3, 2, 1, 0],
}

CAL_ICONS = {"jalali": "🔆", "gregorian": "🌐", "hijri": "🌙"}


def get_event_reminders(conn, events, target_date):
    """Return a list of (prefix, title) tuples for calendar events with a level set.
    Each prefix is like '🔔🔆' or '🔔🔆🎊' (bell + calendar icon + optional confetti).
    """
    cur = conn.cursor()
    cur.execute("SELECT event_id, level FROM event_reminders WHERE level > 0")
    reminder_map = {row["event_id"]: row["level"] for row in cur.fetchall()}

    # First pass: collect events that will appear
    reminded_events = []
    for jdate, ev in events:
        ev_id = ev.get("id")
        if ev_id not in reminder_map:
            continue
        level = reminder_map[ev_id]
        days_until = (jdate - target_date).days
        schedule = EVENT_SCHEDULE.get(level, [])
        if days_until not in schedule:
            continue
        reminded_events.append((jdate, ev, days_until))

    # Compute has_holiday from only the events that will be displayed
    has_holiday = any(ev.get("holiday") for _, ev, _ in reminded_events)

    # Second pass: build the display lines
    lines = []
    for jdate, ev, days_until in reminded_events:
        cal = ev.get("calendar", "jalali")
        icon = CAL_ICONS.get(cal, "📌")
        prefix = f"🔔{icon}"
        if ev.get("holiday"):
            prefix += "🎊"
        elif has_holiday:
            prefix += "  "
        prefix += " "

        title = ev["title_en"]
        if days_until == 0:
            title += " (today)"
        elif days_until == 1:
            title += " tomorrow"
        else:
            title += f" in {days_until} days"
        lines.append((prefix, title))
    return lines


def get_tomorrow_preview(events, target_date, reminded_ids=None):
    """Return tomorrow's events as a list.
    First element is the plain string '📅 Tomorrow:'.
    Subsequent elements are (prefix, title) tuples.
    Skips events whose ID is in reminded_ids."""
    if reminded_ids is None:
        reminded_ids = set()

    tomorrow = target_date + jdatetime.timedelta(days=1)
    tomorrow_events = [(d, ev) for d, ev in events if d == tomorrow]

    # Filter out events that are already reminded for tomorrow
    tomorrow_events = [(d, ev) for d, ev in tomorrow_events if ev.get("id") not in reminded_ids]

    if not tomorrow_events:
        return []

    has_holiday = any(ev.get("holiday") for _, ev in tomorrow_events)
    lines = ["📅 Tomorrow:"]
    for _, ev in tomorrow_events:
        cal = ev.get("calendar", "jalali")
        icon = CAL_ICONS.get(cal, "📌")
        prefix = icon + ("🎊" if ev.get("holiday") else "")
        if not ev.get("holiday") and has_holiday:
            prefix += "  "
        prefix += " "
        lines.append((prefix, ev["title_en"]))
    return lines
