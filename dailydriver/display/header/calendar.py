# dailydriver/display/header/calendar.py
"""Calendar events and reminders header lines."""

import jdatetime

from dailydriver.utils.calendar_events import (
    get_events,
    get_events_for_date,
    get_todays_events,
    get_upcoming_events,
)


def get_calendar_lines(target_date, is_today):
    cal_icons = {"jalali": "🔆", "gregorian": "🌐", "hijri": "🌙"}
    if is_today:
        events = get_events()
        todays = get_todays_events(events)
    else:
        todays = get_events_for_date(target_date)
    lines = []
    for e in todays:
        cal = e.get("calendar", "jalali")
        icon = cal_icons.get(cal, "📌")
        prefix = icon + ("🎊" if e.get("holiday") else "")
        lines.append(f"{prefix} {e['title_en']}")
    return lines


def get_reminders_str(target_date, is_today):
    if not is_today:
        return ""
    events = get_events()
    if not events:
        return ""
    upcoming = get_upcoming_events(events, days=14)
    reminders = [(d, e) for d, e in upcoming if d > target_date and e.get("remind")]
    if not reminders:
        return ""
    rparts = []
    for d, e in reminders[:5]:
        rparts.append(
            f"🔔 {d.day} {jdatetime.date.j_months_fa[d.month-1]}: {e['title_en']}"
        )
    return " | ".join(rparts)
