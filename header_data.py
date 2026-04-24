import time
import jdatetime
from datetime import datetime
from database import get_connection
from utils import today_jalali, format_jalali

def build_header_data():
    """Collect all data needed for the daily header and return a dict."""
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()
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
        "SELECT duration_minutes FROM sleep_logs WHERE jalali_date=?", (today,)
    ).fetchone()
    if sleep_row:
        d = sleep_row['duration_minutes']
        sleep_str = f"💤 Sleep: {d//60}h {d%60}m"
    else:
        sleep_str = "💤 Sleep: —"

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
    cur.execute("SELECT item, desired_interval_days FROM hygiene_config")
    hygiene_items = cur.fetchall()
    nudge_lines = []
    now_ts = int(time.time())
    for item_row in hygiene_items:
        item = item_row['item']
        desired = item_row['desired_interval_days']
        cur.execute('''
            SELECT MAX(e.started_at) as last_time
            FROM entries e
            JOIN entry_categories ec ON e.id = ec.entry_id
            JOIN categories c ON ec.category_id = c.id
            WHERE c.path LIKE ?
        ''', ('%/' + item,))
        last = cur.fetchone()
        if last and last['last_time']:
            days_since = (now_ts - last['last_time']) // 86400
        else:
            days_since = None

        # early warning thresholds
        if desired >= 15:
            early = 3
        elif desired >= 7:
            early = 2
        elif desired >= 2:
            early = 1
        else:
            early = 0

        if days_since is not None and desired > 0:
            due_in = desired - days_since
            if 0 < due_in <= early:
                nudge_lines.append(f"⚠️ {item}: due in {due_in}d (last {days_since}d ago)")
            elif days_since >= desired:
                nudge_lines.append(f"⚠️ {item}: overdue! (last {days_since}d ago)")
    hygiene_str = "   ".join(nudge_lines[:2])

    conn.close()

    return {
        'date_str': formatted,
        'prayer_parts': prayer_parts,
        'sleep_str': sleep_str,
        'bday_str': bday_str,
        'hygiene_str': hygiene_str,
    }
