# dailydriver/display/header/prayer.py
"""Prayer status line and pre‑alert / overdue nudges."""
from datetime import datetime
import jdatetime
from dailydriver.domains.prayer_times import get_approximate_times

def get_prayer_parts(conn, today):
    cur = conn.cursor()
    slot_info = [
        ('fajr', '🌅', 'F'),
        ('dhuhr_asr', '☀️', 'DA'),
        ('maghrib_isha', '🌆', 'MI'),
    ]
    parts = []
    for slot, emoji, _ in slot_info:
        row = cur.execute(
            "SELECT prayer_time FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
            (slot, today)
        ).fetchone()
        if row and row['prayer_time']:
            dt = datetime.fromtimestamp(row['prayer_time'])
            time_str = dt.strftime('%H:%M')
            parts.append(f"{emoji} {time_str}")
        else:
            parts.append(f"{emoji}  — ")
    return parts

def get_prayer_nudges(conn, target_date, today_str, is_today, now=None):
    """Return list of nudge strings (pre‑alert or overdue). Only active for today."""
    if not is_today:
        return []

    if now is None:
        now = datetime.now()

    RED = '\033[31m'
    YELLOW = '\033[33m'
    RESET = '\033[0m'

    nudges = []

    # Helper to read meta
    def _get_complete_until(cursor):
        cursor.execute("SELECT value FROM meta WHERE key='prayer_complete_until'")
        row = cursor.fetchone()
        return row['value'] if row else None

    # Today's prayer times
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

    cur = conn.cursor()
    for slot, dt in slot_times.items():
        minutes_until = (dt - now).total_seconds() // 60
        if 0 <= minutes_until <= 60:
            rounded = max(5, int(round(minutes_until / 5) * 5))
            label = slot.replace('_', ' & ').title()
            nudges.append(f"{YELLOW}🕌 {label} in ~{rounded} min{RESET}")
        elif minutes_until < 0:
            cur.execute(
                "SELECT id FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
                (slot, today_str)
            )
            if not cur.fetchone():
                label = slot.replace('_', ' & ').title()
                nudges.append(f"{RED}⚠️ {label} not logged (today){RESET}")

    # Past overdue scan (up to 5)
    complete_until = _get_complete_until(cur)
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
                cur.execute(
                    "SELECT id FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
                    (slot, date_str)
                )
                if not cur.fetchone():
                    label = slot.replace('_', ' & ').title()
                    day_label = d.strftime('%d %b')
                    nudges.append(f"{RED}⚠️ {label} not logged ({day_label}){RESET}")
                    past_count += 1
                    if past_count >= 5:
                        break
        d -= jdatetime.timedelta(days=1)
    return nudges[:5]
