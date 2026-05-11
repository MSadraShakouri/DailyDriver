# dailydriver/display/header/__init__.py
"""Daily header data builder – delegated to sub‑modules."""
from dailydriver.core.database import get_connection_cm
from dailydriver.utils.time_utils import today_jalali, format_jalali
import jdatetime

from .prayer import get_prayer_parts, get_prayer_nudges
from .sleep import get_sleep_str, get_nap_str
from .birthdays import get_birthday_str
from .hygiene import get_hygiene_str
from .calendar import get_calendar_lines, get_reminders_str
from .events import get_great_event_str, get_running_event_str, get_last_entry_time
from .weather import get_weather_str

def build_header_data(day=None, is_today=True):
    """Collect all data needed for the daily header and return a dict."""
    with get_connection_cm() as conn:
        if day is None:
            today = today_jalali()
            target_date = jdatetime.date.today()
        else:
            today = day
            y, m, d = map(int, day.split('-'))
            target_date = jdatetime.date(y, m, d)

        formatted = format_jalali(today)

        prayer_parts = get_prayer_parts(conn, today)
        sleep_str = get_sleep_str(conn, today)
        nap_str = get_nap_str(conn, today)
        bday_str = get_birthday_str(conn, target_date)
        hygiene_str = get_hygiene_str(conn, target_date, is_today)
        calendar_lines = get_calendar_lines(target_date, is_today)
        reminders_str = get_reminders_str(target_date, is_today)
        great_event_str = get_great_event_str(is_today)
        event_str = get_running_event_str(is_today)
        last_entry_time = get_last_entry_time(is_today)
        weather_str = get_weather_str(conn, today, is_today)
        prayer_nudges = get_prayer_nudges(conn, target_date, today, is_today)

        return {
            'date_str': formatted,
            'prayer_parts': prayer_parts,
            'sleep_str': sleep_str,
            'nap_str': nap_str,
            'bday_str': bday_str,
            'hygiene_str': hygiene_str,
            'calendar_lines': calendar_lines,
            'reminders_str': reminders_str,
            'event_str': event_str,
            'great_event_str': great_event_str,
            'last_entry_time': last_entry_time,
            'weather_str': weather_str,
            'prayer_nudges': prayer_nudges,
            'is_today': is_today,
        }
