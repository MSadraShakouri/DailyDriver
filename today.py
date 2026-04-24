import time
import jdatetime
from datetime import datetime
from database import get_connection
from utils import today_jalali, format_jalali

def show_today():
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()
    formatted = format_jalali(today)

    # Get Jalali date range as Gregorian timestamps
    y, m, d = map(int, today.split('-'))
    jdate = jdatetime.date(y, m, d)
    gdate = jdate.togregorian()
    day_start = int(datetime(gdate.year, gdate.month, gdate.day, 0, 0, 0).timestamp())
    day_end   = int(datetime(gdate.year, gdate.month, gdate.day, 23, 59, 59).timestamp())

    print(f"══════ Today: {formatted} ══════")

    # Prayers
    print("🕌 Prayers:")
    for slot in ['fajr', 'dhuhr_asr', 'maghrib_isha']:
        row = cur.execute(
            "SELECT status FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
            (slot, today)
        ).fetchone()
        if row:
            icon = '✅' if row['status']=='on_time' else ('🕯️' if row['status']=='qada' else '❌')
            print(f"   {slot.replace('_',' ').title()}: {icon}")
        else:
            print(f"   {slot.replace('_',' ').title()}: ⏳")

    # Sleep
    sleep_row = cur.execute(
        "SELECT duration_minutes FROM sleep_logs WHERE jalali_date=?",
        (today,)
    ).fetchone()
    if sleep_row:
        h = sleep_row['duration_minutes'] // 60
        m = sleep_row['duration_minutes'] % 60
        print(f"💤 Sleep: {h}h {m}m")
    else:
        print("💤 Sleep: —")

    # Entries
    print("\n📝 Entries:")
    cur.execute("""
        SELECT e.id, e.description, e.created_at,
               GROUP_CONCAT(DISTINCT c.path) AS cats,
               GROUP_CONCAT(DISTINCT f.token) AS flags
        FROM entries e
        LEFT JOIN entry_categories ec ON e.id = ec.entry_id
        LEFT JOIN categories c ON ec.category_id = c.id
        LEFT JOIN entry_flags ef ON e.id = ef.entry_id
        LEFT JOIN flags f ON ef.flag_id = f.id
        WHERE e.created_at BETWEEN ? AND ?
        GROUP BY e.id
        ORDER BY e.created_at ASC
    """, (day_start, day_end))
    entries = cur.fetchall()

    if not entries:
        print("   No entries yet today.")
    else:
        for e in entries:
            dt = datetime.fromtimestamp(e['created_at']).strftime('%H:%M')
            cats = e['cats'] or '(no category)'
            flags = f" [{e['flags']}]" if e['flags'] else ""
            desc = (e['description'] or '')[:50].replace('\n', ' ')
            print(f"   {dt}  {cats}{flags}")
            if desc:
                print(f"         {desc}")

    conn.close()
