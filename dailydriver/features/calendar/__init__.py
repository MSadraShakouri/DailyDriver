# dailydriver/features/calendar/__init__.py
"""Calendar feature – events, reminders, commands (cal, year, hijri)."""

from . import _commands, _header, _logic, _reminders

NAME = "calendar"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["cal"] = _commands.show_calendar
    dispatch["year"] = _commands.show_year
    dispatch["hijri"] = _commands.hijri_command


def header_sections(conn, today, target_date, is_today):
    all_events = _logic.get_events() or []

    # --- event reminders (bell lines) ---
    reminder_lines = _reminders.get_event_reminders(conn, all_events, target_date)

    # --- suppressed calendar lines (filter out today‑reminded events) ---
    reminded_today_ids = set()
    cur = conn.cursor()
    for jdate, ev in all_events:
        ev_id = ev.get("id")
        if ev_id is not None:
            cur.execute(
                "SELECT level FROM event_reminders WHERE event_id=? AND level > 0",
                (ev_id,),
            )
            row = cur.fetchone()
            if row:
                level = row["level"]
                schedule = _reminders.EVENT_SCHEDULE.get(level, [])
                if 0 in schedule and (jdate - target_date).days == 0:
                    reminded_today_ids.add(ev_id)

    calendar_lines = _header.get_calendar_lines(target_date, is_today, reminded_today_ids)

    # --- tomorrow preview ---
    reminded_tomorrow_ids = set()
    for jdate, ev in all_events:
        ev_id = ev.get("id")
        if ev_id is not None:
            cur.execute(
                "SELECT level FROM event_reminders WHERE event_id=? AND level > 0",
                (ev_id,),
            )
            row = cur.fetchone()
            if row:
                level = row["level"]
                schedule = _reminders.EVENT_SCHEDULE.get(level, [])
                if 1 in schedule and (jdate - target_date).days == 1:
                    reminded_tomorrow_ids.add(ev_id)

    tomorrow_lines = _reminders.get_tomorrow_preview(all_events, target_date, reminded_tomorrow_ids)

    # --- old reminders_str (kept for backward compat, if still used) ---
    reminders_str = _header.get_reminders_str(target_date, is_today)

    # --- assemble results with priorities ---
    result = []
    if reminder_lines:
        result.append((33, ""))  # breather before reminders
        for line in reminder_lines:
            result.append((34, line))
    if tomorrow_lines:
        result.append((35, ""))  # breather before tomorrow
        for line in tomorrow_lines:
            result.append((36, line))
    if calendar_lines:
        result.append((37, ""))  # breather before today's events
        for line in calendar_lines:
            result.append((38, line))
    if reminders_str:
        result.append((39, reminders_str))
    return result

    return result
