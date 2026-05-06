# dailydriver/display/header.py
import time
import jdatetime
from datetime import datetime
from dailydriver.core.database import get_connection_cm
from dailydriver.display.hygiene_nudges import compute_hygiene_nudges
from dailydriver.utils.time_utils import today_jalali, format_jalali
from dailydriver.core.logger import get_pending_start, get_active_great_event
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.calendar_events import get_events, get_todays_events, get_upcoming_events
from dailydriver.utils.weather import get_weather

def build_header_data():
    """Collect all data needed for the daily header and return a dict."""
    with get_connection_cm() as conn:
        cur = conn.cursor()

        today = today_jalali()
        formatted = format_jalali(today)

        # Add abbreviated English weekday (e.g., Sat)
        weekdays_en = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        # Get Gregorian weekday from today's Jalali date
        today_j = jdatetime.date(*map(int, today.split('-')))
        gdate = today_j.togregorian()
        wday = weekdays_en[gdate.weekday()]   # 0=Monday
        formatted = f"{wday}, {formatted}"

        # ---------- prayer status ----------
        slot_info = [
            ('fajr', '🌅', 'F'),
            ('dhuhr_asr', '☀️', 'DA'),
            ('maghrib_isha', '🌆', 'MI'),
        ]
        prayer_parts = []
        for slot, emoji, label in slot_info:
            row = cur.execute(
                "SELECT prayer_time FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
                (slot, today)
            ).fetchone()
            if row and row['prayer_time']:
                dt = datetime.fromtimestamp(row['prayer_time'])
                time_str = dt.strftime('%H:%M')
                prayer_parts.append(f"{emoji} {time_str}")
            else:
                prayer_parts.append(f"{emoji} —")

        # ---------- sleep ----------
        sleep_row = cur.execute(
            "SELECT duration_minutes FROM sleep_logs WHERE jalali_date=?", (today,)
        ).fetchone()
        if sleep_row:
            d = sleep_row['duration_minutes']
            sleep_str = f"💤 Sleep: {d//60}h {d%60}m"
        else:
            sleep_str = "💤 Sleep: —"

        # ---------- naps ----------
        nap_row = cur.execute(
            "SELECT SUM(duration_minutes) FROM nap_logs WHERE jalali_date=?", (today,)
        ).fetchone()
        total_nap = nap_row[0] if nap_row and nap_row[0] is not None else 0
        if total_nap:
            nap_str = f"😴 Nap: {total_nap//60}h {total_nap%60}m"
        else:
            nap_str = ""

        # ---------- weather ----------
        weather = get_weather()
        weather_str = ""
        if weather:
            cond = weather['condition_en'] if weather['condition_en'] else weather['condition_fa']
            weather_str = f"🌡️ {weather['temp_c']}°C {cond}"
            # Show timestamp only if older than 1 hour
            if time.time() - weather['timestamp'] > 3600:
                jd = jdatetime.datetime.fromtimestamp(weather['timestamp'])
                weather_str += f" {jd.strftime('%H:%M')}"

        # ---------- birthdays (next 7 days) ----------
        today_j = jdatetime.date.today()
        bday_lines = []
        for i in range(7):
            check_date = today_j + jdatetime.timedelta(days=i)
            m, d = check_date.month, check_date.day
            cur.execute("SELECT name, year FROM birthdays WHERE month=? AND day=?", (m, d))
            for row in cur.fetchall():
                age = ""
                if row['year']:
                    age = f" ({check_date.year - row['year']})"
                prefix = "🎂" if i == 0 else f"🎈{i}d"
                bday_lines.append(f"{prefix} {row['name']}{age}")
        bday_str = "   ".join(bday_lines[:3])

        # ---------- hygiene nudges ----------
        nudge_lines = compute_hygiene_nudges(conn)
        hygiene_str = "   ".join(nudge_lines[:2])

        # ---------- today's events from calendar ----------
        events = get_events()
        todays = get_todays_events(events)
        calendar_lines = []
        if todays:
            cal_icons = {'jalali': '🔆', 'gregorian': '🌐', 'hijri': '🌙'}
            holiday_icon = '🎊'
            for e in todays:
                cal = e.get('calendar', 'jalali')
                prefix = cal_icons.get(cal, '📌')
                if e.get('holiday'):
                    prefix += holiday_icon
                calendar_lines.append(f"{prefix} {e['title_en']}")

        # ---------- upcoming reminders (events with remind:true in the next 14 days) ----------
        reminders_str = ""
        if events:
            today_j = jdatetime.date.today()
            upcoming = get_upcoming_events(events, days=14)
            # Only events that are in the future (starting tomorrow) and have remind=True
            reminders = [(d, e) for d, e in upcoming if d > today_j and e.get('remind')]
            if reminders:
                rparts = []
                for d, e in reminders[:5]:          # show up to 5
                    rparts.append(f"🔔 {d.day} {jdatetime.date.j_months_fa[d.month-1]}: {e['title_en']}")
                reminders_str = " | ".join(rparts)

        # ---------- great event indicator ----------
        great_event_str = ''
        active_ge = get_active_great_event()
        if active_ge:
            start_ts, cats = active_ge
            from datetime import datetime as dt
            time_str = dt.fromtimestamp(start_ts).strftime('%H:%M')
            great_event_str = f"⏱ Great Event [{', '.join(cats)}] since {time_str}"

        # ---------- running event indicator ----------
        event_str = ""
        ts = get_pending_start()
        if ts is not None:
            dt = datetime.fromtimestamp(ts)
            event_str = f"⏱ Event running since {dt.strftime('%H:%M')}"

        # ---------- last action time for header ----------
        from dailydriver.core.logger import get_last_action_time
        last_ts = get_last_action_time()
        last_entry_time = ''
        if last_ts is not None:
            dt = datetime.fromtimestamp(last_ts)
            last_entry_time = dt.strftime('%H:%M')

        return {
            'date_str': formatted,
            'prayer_parts': prayer_parts,
            'sleep_str': sleep_str,
            'bday_str': bday_str,
            'hygiene_str': hygiene_str,
            'calendar_lines': calendar_lines,
            'reminders_str': reminders_str,
            'event_str': event_str,
            'great_event_str': great_event_str,
            'last_entry_time': last_entry_time,
            'nap_str': nap_str,
            'weather_str': weather_str,
        }
