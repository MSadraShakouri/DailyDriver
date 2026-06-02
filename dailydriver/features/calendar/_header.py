# dailydriver/display/header/calendar.py
"""Calendar events and reminders header lines."""

import jdatetime

from . import _logic


def get_calendar_lines(target_date, is_today, reminded_ids=None):
    cal_icons = {"jalali": "🔆", "gregorian": "🌐", "hijri": "🌙"}
    if is_today:
        events = _logic.get_events()
        todays = _logic.get_todays_events(events)
    else:
        todays = _logic.get_events_for_date(target_date)

    if reminded_ids:
        todays = [e for e in todays if e.get("id") not in reminded_ids]

    has_holiday = any(e.get("holiday") for e in todays)
    lines = []
    for e in todays:
        cal = e.get("calendar", "jalali")
        icon = cal_icons.get(cal, "📌")
        prefix = icon + ("🎊" if e.get("holiday") else "")
        if not e.get("holiday") and has_holiday:
            prefix += "  "
        prefix += " "
        lines.append((prefix, e["title_en"]))
    return lines


def get_reminders_str(target_date, is_today):
    if not is_today:
        return ""
    events = _logic.get_events()
    if not events:
        return ""
    upcoming = _logic.get_upcoming_events(events, days=14)
    reminders = [(d, e) for d, e in upcoming if d > target_date and e.get("remind")]
    if not reminders:
        return ""
    rparts = []
    for d, e in reminders[:5]:
        rparts.append(f"🔔 {d.day} {jdatetime.date.j_months_fa[d.month-1]}: {e['title_en']}")
    return " | ".join(rparts)
