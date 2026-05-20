# dailydriver/display/header/__init__.py
"""Daily header data builder – delegated to sub‑modules."""

from datetime import timedelta

import jdatetime
from hijridate import Gregorian as HijriGregorian

from dailydriver.core.database import get_connection_cm
from dailydriver.display.display_utils import get_width, spread_line
from dailydriver.utils.calendar_events import get_hijri_offset
from dailydriver.utils.time_utils import format_jalali, today_jalali

from .birthdays import get_birthday_str
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

        # --- new date block ---
        jalali_line = f"\033[1m{formatted}\033[0m"
        separator = "─" * (get_width() // 4)

        # Gregorian and Hijri with margins
        gdate = target_date.togregorian()
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
        bday_str = get_birthday_str(conn, target_date)
        hygiene_lines = get_hygiene_lines(conn, target_date, is_today)
        calendar_lines = get_calendar_lines(target_date, is_today)
        reminders_str = get_reminders_str(target_date, is_today)
        great_event_str = get_great_event_str(is_today)
        event_str = get_running_event_str(is_today)
        last_entry_time = get_last_entry_time(is_today)
        weather_str = get_weather_str(conn, today, is_today)
        prayer_nudges = get_prayer_nudges(conn, target_date, today, is_today)

        return {
            "jalali_line": jalali_line,
            "separator": separator,
            "greg_hijri_line": greg_hijri_line,
            "date_str": formatted,
            "prayer_parts": prayer_parts,
            "sleep_str": sleep_str,
            "nap_str": nap_str,
            "bday_str": bday_str,
            "hygiene_lines": hygiene_lines,
            "calendar_lines": calendar_lines,
            "reminders_str": reminders_str,
            "event_str": event_str,
            "great_event_str": great_event_str,
            "last_entry_time": last_entry_time,
            "weather_str": weather_str,
            "prayer_nudges": prayer_nudges,
            "is_today": is_today,
        }
