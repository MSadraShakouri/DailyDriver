# dailydriver/display/header.py
import time
import jdatetime
from datetime import datetime, timedelta
from dailydriver.core.database import get_connection_cm
from dailydriver.display.hygiene_nudges import compute_hygiene_nudges
from dailydriver.utils.time_utils import today_jalali, format_jalali
from dailydriver.core.logger import get_pending_start, get_active_great_event
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.calendar_events import get_events, get_todays_events, get_upcoming_events, get_events_for_date
from dailydriver.domains.prayer_times import get_approximate_times
from dailydriver.domains.prayer_core import PRAYER_SLOTS

def build_header_data(day=None, is_today=True):
    """Collect all data needed for the daily header and return a dict."""
    with get_connection_cm() as conn:
        cur = conn.cursor()

        if day is None:
            today = today_jalali()
            target_date = jdatetime.date.today()
        else:
            today = day
            y, m, d = map(int, day.split('-'))
            target_date = jdatetime.date(y, m, d)

        formatted = format_jalali(today)

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
            "SELECT sleep_time, wake_time, duration_minutes FROM sleep_logs WHERE jalali_date=?", (today,)
        ).fetchone()
        if sleep_row:
            start_dt = datetime.fromtimestamp(sleep_row['sleep_time'])
            end_dt = datetime.fromtimestamp(sleep_row['wake_time'])
            d = sleep_row['duration_minutes']
            sleep_str = f"💤 Sleep: {d//60}h {d%60}m ({start_dt.strftime('%H:%M')} → {end_dt.strftime('%H:%M')})"
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

        # ---------- birthdays (next 7 days) ----------
        bday_lines = []
        for i in range(7):
            check_date = target_date + jdatetime.timedelta(days=i)
            m_day, d_day = check_date.month, check_date.day
            cur.execute("SELECT name, year FROM birthdays WHERE month=? AND day=?", (m_day, d_day))
            for row in cur.fetchall():
                age = ""
                if row['year']:
                    age = f" ({check_date.year - row['year']})"
                prefix = "🎂" if i == 0 else f"🎈{i}d"
                bday_lines.append(f"{prefix} {row['name']}{age}")
        bday_str = "   ".join(bday_lines[:3])

        # ---------- hygiene nudges only for today ----------
        if is_today:
            nudge_lines = compute_hygiene_nudges(conn, relative_to=target_date)
        else:
            nudge_lines = []
        hygiene_str = "   ".join(nudge_lines[:2])

        # ---------- today's events from calendar ----------
        cal_icons = {'jalali': '🔆', 'gregorian': '🌐', 'hijri': '🌙'}
        if not is_today:   # past or future
            todays_events = get_events_for_date(target_date)
            calendar_lines = []
            if todays_events:
                for e in todays_events:
                    cal = e.get('calendar', 'jalali')
                    icon = cal_icons.get(cal, '📌')
                    prefix = icon + ('🎊' if e.get("holiday") else '')
                    calendar_lines.append(f"{prefix} {e['title_en']}")
        else:
            events = get_events()
            todays = get_todays_events(events)
            calendar_lines = []
            if todays:
                for e in todays:
                    cal = e.get('calendar', 'jalali')
                    icon = cal_icons.get(cal, '📌')
                    prefix = icon + ('🎊' if e.get("holiday") else '')
                    calendar_lines.append(f"{prefix} {e['title_en']}")

        # ---------- reminders (only for today) ----------
        reminders_str = ""
        if is_today:
            events = get_events()
            if events:
                upcoming = get_upcoming_events(events, days=14)
                reminders = [(d, e) for d, e in upcoming if d > target_date and e.get('remind')]
                if reminders:
                    rparts = []
                    for d, e in reminders[:5]:
                        rparts.append(f"🔔 {d.day} {jdatetime.date.j_months_fa[d.month-1]}: {e['title_en']}")
                    reminders_str = " | ".join(rparts)

        # ---------- great event (only today) ----------
        great_event_str = ''
        if is_today:
            active_ge = get_active_great_event()
            if active_ge:
                start_ts, cats = active_ge
                time_str = datetime.fromtimestamp(start_ts).strftime('%H:%M')
                great_event_str = f"⏱ Great Event [{', '.join(cats)}] since {time_str}"

        # ---------- running event (only today) ----------
        event_str = ""
        if is_today:
            ts = get_pending_start()
            if ts is not None:
                dt = datetime.fromtimestamp(ts)
                event_str = f"⏱ Event running since {dt.strftime('%H:%M')}"

        # ---------- last action time (only today) ----------
        last_entry_time = ''
        if is_today:
            from dailydriver.core.logger import get_last_action_time
            last_ts = get_last_action_time()
            if last_ts is not None:
                dt = datetime.fromtimestamp(last_ts)
                last_entry_time = dt.strftime('%H:%M')

        # ---------- weather ----------
        weather_str = ""
        if not is_today:
            # For past/future days, use cached weather from that day
            y, m2, d2 = map(int, today.split('-'))
            gdate = jdatetime.date(y, m2, d2).togregorian()
            gstart = datetime(gdate.year, gdate.month, gdate.day, 0, 0, 0)
            gend = gstart + timedelta(hours=24)
            wrow = cur.execute(
                "SELECT temp_c, condition_fa, timestamp FROM weather_log WHERE timestamp BETWEEN ? AND ? ORDER BY id DESC LIMIT 1",
                (int(gstart.timestamp()), int(gend.timestamp()))
            ).fetchone()
            if wrow:
                from dailydriver.utils.weather import _translate_condition
                cond_info = _translate_condition(wrow['condition_fa'])
                cond_en = cond_info['en'] if cond_info and cond_info.get('en') != 'NOT TRANSLATED' else wrow['condition_fa']
                emoji = cond_info.get('emoji', '🌡️') if cond_info else '🌡️'
                weather_str = f"{emoji} {wrow['temp_c']}°C {cond_en}"
        else:
            from dailydriver.utils.weather import get_weather
            weather = get_weather()
            if weather:
                cond = weather['condition_en'] if weather['condition_en'] else weather['condition_fa']
                emoji = weather.get('condition_emoji', '🌡️')
                weather_str = f"{emoji} {weather['temp_c']}°C {cond}"
                if time.time() - weather['timestamp'] > 3600:
                    jd = jdatetime.datetime.fromtimestamp(weather['timestamp'])
                    weather_str += f" {jd.strftime('%H:%M')}"

        # ---------- prayer nudges (pre‑alert & overdue) only for today ----------
        prayer_nudges = []
        now = datetime.now()
        if is_today:
            def _get_prayer_complete_until(conn):
                cur = conn.cursor()
                cur.execute("SELECT value FROM meta WHERE key='prayer_complete_until'")
                row = cur.fetchone()
                return row['value'] if row else None

            today_j = jdatetime.date.today()
            approx = get_approximate_times(today_j.month, today_j.day)
            g = today_j.togregorian()
            fajr_dt = datetime(g.year, g.month, g.day, approx['fajr'][0], approx['fajr'][1], 0)
            dhuhr_dt = datetime(g.year, g.month, g.day, approx['dhuhr'][0], approx['dhuhr'][1], 0)
            maghrib_dt = datetime(g.year, g.month, g.day, approx['maghrib'][0], approx['maghrib'][1], 0)
            slot_times = {
                'fajr': fajr_dt,
                'dhuhr_asr': dhuhr_dt,
                'maghrib_isha': maghrib_dt,
            }
            cur2 = conn.cursor()
            for slot, dt in slot_times.items():
                minutes_until = (dt - now).total_seconds() // 60
                if 0 <= minutes_until <= 60:
                    rounded = max(5, int(round(minutes_until / 5) * 5))
                    label = slot.replace('_', ' & ').title()
                    prayer_nudges.append(f"🕌 {label} in ~{rounded} min")
                elif minutes_until < 0:
                    cur2.execute(
                        "SELECT id FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
                        (slot, today)
                    )
                    if not cur2.fetchone():
                        label = slot.replace('_', ' & ').title()
                        prayer_nudges.append(f"⚠️ {label} not logged (today)")

            # Past overdue scan (up to 5 most recent)
            complete_until = _get_prayer_complete_until(conn)
            if complete_until:
                cu_y, cu_m, cu_d = map(int, complete_until.split('-'))
                complete_j = jdatetime.date(cu_y, cu_m, cu_d)
            else:
                complete_j = target_date - jdatetime.timedelta(days=6)
            d = target_date - jdatetime.timedelta(days=1)
            past_count = 0
            while d > complete_j and past_count < 5:
                date_str = d.strftime('%Y-%m-%d')
                approx_past = get_approximate_times(d.month, d.day)
                gd = d.togregorian()
                try:
                    fajr_dt_p = datetime(gd.year, gd.month, gd.day,
                                        approx_past['fajr'][0], approx_past['fajr'][1], 0)
                    dhuhr_dt_p = datetime(gd.year, gd.month, gd.day,
                                         approx_past['dhuhr'][0], approx_past['dhuhr'][1], 0)
                    maghrib_dt_p = datetime(gd.year, gd.month, gd.day,
                                            approx_past['maghrib'][0], approx_past['maghrib'][1], 0)
                except ValueError:
                    d -= jdatetime.timedelta(days=1)
                    continue
                past_slots = {
                    'fajr': fajr_dt_p,
                    'dhuhr_asr': dhuhr_dt_p,
                    'maghrib_isha': maghrib_dt_p,
                }
                for slot, slot_dt in past_slots.items():
                    if slot_dt <= now:
                        cur2.execute(
                            "SELECT id FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
                            (slot, date_str)
                        )
                        if not cur2.fetchone():
                            label = slot.replace('_', ' & ').title()
                            day_label = d.strftime('%d %b')
                            prayer_nudges.append(f"⚠️ {label} not logged ({day_label})")
                            past_count += 1
                            if past_count >= 5:
                                break
                d -= jdatetime.timedelta(days=1)

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
            'prayer_nudges': prayer_nudges[:5],
            'is_today': is_today,
        }
