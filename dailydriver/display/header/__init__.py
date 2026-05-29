# dailydriver/display/header/__init__.py
"""Daily header data builder – delegated to sub‑modules."""

from datetime import timedelta

import jdatetime
from hijridate import Gregorian as HijriGregorian

import dailydriver.features as features_pkg
from dailydriver.core.database import get_connection_cm
from dailydriver.display.display_utils import get_width, spread_line
from dailydriver.utils.calendar_events import get_events, get_hijri_offset
from dailydriver.utils.event_reminders import (
    EVENT_SCHEDULE,
    get_event_reminders,
    get_tomorrow_preview,
)
from dailydriver.utils.time_utils import format_jalali, today_jalali

from .birthdays import get_birthday_lines
from .calendar import get_calendar_lines, get_reminders_str
from .events import get_great_event_str, get_last_entry_time, get_running_event_str
from .hygiene import get_hygiene_lines
from .prayer import get_prayer_nudges, get_prayer_parts
from .sleep import get_nap_str, get_sleep_str
from .weather import get_weather_str


def build_header_data(day=None, is_today=True):
    """Collect all data needed for the daily header and return a dict."""
    with get_connection_cm() as conn:
        if day is None:
            today = today_jalali()
            target_date = jdatetime.date.today()
        else:
            today = day
            y, m, d = map(int, day.split("-"))
            target_date = jdatetime.date(y, m, d)

        formatted = format_jalali(today)
        # Prepend weekday abbreviation (e.g., "Sun, ")
        gdate = target_date.togregorian()
        weekday_abbr = gdate.strftime("%a")
        formatted = f"{weekday_abbr}, {formatted}"

        # --- new date block ---
        jalali_line = f"\033[1m{formatted}\033[0m"
        separator = "─" * (get_width() // 4)

        # Gregorian and Hijri with margins
        greg_str = gdate.strftime("%d %B %Y")
        offset = get_hijri_offset()
        corrected_greg = gdate - timedelta(days=offset)
        hijri_obj = HijriGregorian.fromdate(corrected_greg).to_hijri()
        hijri_str = f"{hijri_obj.day} {hijri_obj.month_name()} {hijri_obj.year}"
        greg_hijri_line = spread_line([greg_str, hijri_str], margins=1 / 8)

        if not is_today:
            jalali_line = f"\033[2m\033[1m{formatted}\033[0m"
            separator = f"\033[2m{separator}\033[0m"
            greg_hijri_line = f"\033[2m{greg_hijri_line}\033[0m"

        prayer_parts = get_prayer_parts(conn, today)
        sleep_str = get_sleep_str(conn, today)
        nap_str = get_nap_str(conn, today)
        bday_lines = get_birthday_lines(conn, target_date)
        hygiene_lines = get_hygiene_lines(conn, target_date, is_today)
        reminders_str = get_reminders_str(target_date, is_today)

        # Event reminders and tomorrow preview
        all_events = get_events() or []
        event_reminder_lines = get_event_reminders(conn, all_events, target_date)

        # Compute IDs of events that are reminded for tomorrow (days_until == 1)
        reminded_tomorrow_ids = set()
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
                    schedule = EVENT_SCHEDULE.get(level, [])
                    if 1 in schedule and (jdate - target_date).days == 1:
                        reminded_tomorrow_ids.add(ev_id)

        # Pass reminded_tomorrow_ids to tomorrow preview
        tomorrow_lines = get_tomorrow_preview(
            all_events, target_date, reminded_tomorrow_ids
        )

        # Suppress today's events that already appear as reminders
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
                    schedule = EVENT_SCHEDULE.get(level, [])
                    if 0 in schedule and (jdate - target_date).days == 0:
                        reminded_today_ids.add(ev_id)

        # Build calendar lines with reminder suppression for the target day
        cal_icons = {"jalali": "🔆", "gregorian": "🌐", "hijri": "🌙"}
        events_target = [ev for d, ev in all_events if d == target_date]
        # Filter out events that are already reminded for this day
        display_events = [
            ev for ev in events_target if ev.get("id") not in reminded_today_ids
        ]
        has_holiday = any(ev.get("holiday") for ev in display_events)
        calendar_lines = []
        for ev in display_events:
            cal = ev.get("calendar", "jalali")
            icon = cal_icons.get(cal, "📌")
            prefix = icon + ("🎊" if ev.get("holiday") else "")
            if not ev.get("holiday") and has_holiday:
                prefix += "  "
            prefix += " "
            calendar_lines.append((prefix, ev["title_en"]))

        great_event_str = get_great_event_str(is_today)
        event_str = get_running_event_str(is_today)
        last_entry_time = get_last_entry_time(is_today)
        weather_str = get_weather_str(conn, today, is_today)
        prayer_nudges = get_prayer_nudges(conn, target_date, today, is_today)

        # Collect header lines from enabled feature packages
        feature_lines = []
        for feature in features_pkg.ENABLED:
            if hasattr(feature, "header_sections"):
                lines = feature.header_sections(conn, today, target_date, is_today)
                if isinstance(lines, list):
                    # lines can be plain strings or (priority, text) tuples
                    feature_lines.extend(lines)
        # Sort by priority (if tuples), then extract text
        if feature_lines and isinstance(feature_lines[0], tuple):
            feature_lines.sort(key=lambda x: x[0])
            feature_lines = [text for _, text in feature_lines]

        return {
            "jalali_line": jalali_line,
            "separator": separator,
            "greg_hijri_line": greg_hijri_line,
            "prayer_parts": prayer_parts,
            "sleep_str": sleep_str,
            "nap_str": nap_str,
            "bday_lines": bday_lines,
            "hygiene_lines": hygiene_lines,
            "calendar_lines": calendar_lines,
            "reminders_str": reminders_str,
            "event_reminder_lines": event_reminder_lines,
            "tomorrow_lines": tomorrow_lines,
            "event_str": event_str,
            "great_event_str": great_event_str,
            "last_entry_time": last_entry_time,
            "weather_str": weather_str,
            "prayer_nudges": prayer_nudges,
            "is_today": is_today,
        }
