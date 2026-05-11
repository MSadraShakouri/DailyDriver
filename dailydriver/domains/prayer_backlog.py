# dailydriver/domains/prayer_backlog.py
import time
import jdatetime
from datetime import datetime, timedelta
from dailydriver.core.database import get_connection_cm
from dailydriver.domains.prayer_core import PRAYER_SLOTS
from dailydriver.domains.prayer_times import get_approximate_times
from dailydriver.utils.time_utils import today_jalali
from dailydriver.ui.terminal_ui import current_ui

def _get_complete_until(conn):
    cur = conn.cursor()
    cur.execute("SELECT value FROM meta WHERE key='prayer_complete_until'")
    row = cur.fetchone()
    return row['value'] if row else None

def _set_complete_until(conn, date_str):
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('prayer_complete_until', ?)", (date_str,))

def _update_complete_until(conn):
    today = today_jalali()
    cur = conn.cursor()
    complete_until = _get_complete_until(conn)
    if complete_until is None:
        # initialize: find earliest prayer log date
        cur.execute("SELECT MIN(jalali_date) FROM prayer_logs")
        row = cur.fetchone()
        if row and row[0]:
            start_str = row[0]
        else:
            _set_complete_until(conn, today)
            return
    else:
        start_str = complete_until
    y, m, d = map(int, start_str.split('-'))
    d_date = jdatetime.date(y, m, d)
    # Advance to last fully logged date
    while d_date <= jdatetime.date.today():
        date_str = d_date.strftime('%Y-%m-%d')
        complete = True
        for slot in PRAYER_SLOTS:
            cur.execute("SELECT id FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?", (slot, date_str))
            if not cur.fetchone():
                complete = False
                break
        if not complete:
            break
        d_date += jdatetime.timedelta(days=1)
    new_until = (d_date - jdatetime.timedelta(days=1)).strftime('%Y-%m-%d')
    _set_complete_until(conn, new_until)

def _get_unlogged_past_slots(conn):
    today = today_jalali()
    complete_until = _get_complete_until(conn)
    if not complete_until:
        _update_complete_until(conn)
        complete_until = _get_complete_until(conn)
    if not complete_until:
        return []
    start_y, start_m, start_d = map(int, complete_until.split('-'))
    start_date = jdatetime.date(start_y, start_m, start_d) + jdatetime.timedelta(days=1)
    end_date = jdatetime.date.today()
    now = datetime.now()
    missing = []
    d = start_date
    while d <= end_date:
        date_str = d.strftime('%Y-%m-%d')
        approx = get_approximate_times(d.month, d.day)
        gdate = d.togregorian()
        try:
            fajr_dt = datetime(gdate.year, gdate.month, gdate.day, approx['fajr'][0], approx['fajr'][1], 0)
            dhuhr_dt = datetime(gdate.year, gdate.month, gdate.day, approx['dhuhr'][0], approx['dhuhr'][1], 0)
            maghrib_dt = datetime(gdate.year, gdate.month, gdate.day, approx['maghrib'][0], approx['maghrib'][1], 0)
        except ValueError:
            d += jdatetime.timedelta(days=1)
            continue
        slot_times = {
            'fajr': fajr_dt,
            'dhuhr_asr': dhuhr_dt,
            'maghrib_isha': maghrib_dt,
        }
        for slot in PRAYER_SLOTS:
            cur = conn.cursor()
            cur.execute("SELECT id FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?", (slot, date_str))
            if not cur.fetchone() and slot_times[slot] <= now:
                missing.append((date_str, slot))
        d += jdatetime.timedelta(days=1)
    missing.sort(key=lambda x: x[0], reverse=True)
    return missing

def log_qada(time_of_day_minutes=None, offset_minutes=None):
    with get_connection_cm() as conn:
        missing = _get_unlogged_past_slots(conn)
        if not missing:
            current_ui.print_line("No overdue prayers to mark as qada.")
            return
        current_ui.print_line("Unlogged past prayers (newest first):")
        for i, (date_str, slot) in enumerate(missing, 1):
            current_ui.print_line(f"  [{i}] {date_str}  {slot}")
        choice = current_ui.prompt("Select number (Enter=latest, q=quit): ").strip().lower()
        if choice == 'q':
            return
        if choice == '':
            idx = 0
        else:
            try:
                idx = int(choice) - 1
                if idx < 0 or idx >= len(missing):
                    current_ui.print_line("Invalid number.")
                    return
            except ValueError:
                current_ui.print_line("Invalid input.")
                return
        date_str, slot = missing[idx]
        y, m, d = map(int, date_str.split('-'))
        jdate = jdatetime.date(y, m, d)
        gdate = jdate.togregorian()
        if time_of_day_minutes is not None:
            hour = time_of_day_minutes // 60
            minute = time_of_day_minutes % 60
            prayer_dt = datetime(gdate.year, gdate.month, gdate.day, hour, minute, 0)
        elif offset_minutes is not None:
            now_dt = datetime.now()
            prayer_dt = now_dt - timedelta(minutes=offset_minutes)
            prayer_dt = prayer_dt.replace(year=gdate.year, month=gdate.month, day=gdate.day)
        else:
            approx = get_approximate_times(m, d)
            if slot == 'fajr':
                hour, minute = approx['fajr']
            elif slot == 'dhuhr_asr':
                hour, minute = approx['dhuhr']
            else:
                hour, minute = approx['maghrib']
            prayer_dt = datetime(gdate.year, gdate.month, gdate.day, hour, minute, 0)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time) VALUES (?,?,?,?,?)",
            (slot, date_str, 'qada', int(time.time()), int(prayer_dt.timestamp()))
        )
        conn.commit()
        time_str = prayer_dt.strftime('%H:%M')
        current_ui.print_line(f"Marked {slot} on {date_str} as qada (time: {time_str}).")
        _update_complete_until(conn)
        conn.commit()
