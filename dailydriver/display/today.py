import jdatetime
from datetime import datetime, timedelta
from dailydriver.core.database import get_connection_cm
from dailydriver.utils.time_utils import today_jalali, format_jalali
from dailydriver.ui.terminal_ui import current_ui

def show_today():
    with get_connection_cm() as conn:
        cur = conn.cursor()

        today = today_jalali()
        formatted = format_jalali(today)

        # Get Jalali date range as Gregorian timestamps
        y, m, d = map(int, today.split('-'))
        jdate = jdatetime.date(y, m, d)
        gdate = jdate.togregorian()
        day_start = int(datetime(gdate.year, gdate.month, gdate.day, 0, 0, 0).timestamp())
        day_end   = int(datetime(gdate.year, gdate.month, gdate.day, 23, 59, 59).timestamp())

        current_ui.print_line(f"══════ Today: {formatted} ══════")

        # Prayers
        current_ui.print_line("🕌 Prayers:")
        for slot in ['fajr', 'dhuhr_asr', 'maghrib_isha']:
            row = cur.execute(
                "SELECT status FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
                (slot, today)
            ).fetchone()
            if row:
                icon = '✅' if row['status']=='on_time' else ('🕯️' if row['status']=='qada' else '❌')
                current_ui.print_line(f"   {slot.replace('_',' ').title()}: {icon}")
            else:
                current_ui.print_line(f"   {slot.replace('_',' ').title()}: ⏳")

        # Sleep
        sleep_row = cur.execute(
            "SELECT duration_minutes FROM sleep_logs WHERE jalali_date=?",
            (today,)
        ).fetchone()
        if sleep_row:
            h = sleep_row['duration_minutes'] // 60
            m = sleep_row['duration_minutes'] % 60
            current_ui.print_line(f"💤 Sleep: {h}h {m}m")
        else:
            current_ui.print_line("💤 Sleep: —")

        # Naps
        nap_rows = cur.execute(
            "SELECT start_time, duration_minutes FROM nap_logs WHERE jalali_date=? ORDER BY start_time",
            (today,)
        ).fetchall()
        if nap_rows:
            current_ui.print_line("😴 Naps:")
            for r in nap_rows:
                start_dt = datetime.fromtimestamp(r['start_time'])
                dur = r['duration_minutes']
                end_dt = start_dt + timedelta(minutes=dur)
                current_ui.print_line(f"   {start_dt.strftime('%H:%M')} → {end_dt.strftime('%H:%M')} ({dur//60}h {dur%60}m)")

        # Entries
        current_ui.print_line("\n📝 Entries:")
        cur.execute("""
            SELECT e.id, e.description, e.created_at,
                   GROUP_CONCAT(DISTINCT c.path) AS cats
            FROM entries e
            LEFT JOIN entry_categories ec ON e.id = ec.entry_id
            LEFT JOIN categories c ON ec.category_id = c.id
            WHERE e.created_at BETWEEN ? AND ?
            GROUP BY e.id
            ORDER BY e.created_at ASC
        """, (day_start, day_end))
        entries = cur.fetchall()

        if not entries:
            current_ui.print_line("   No entries yet today.")
        else:
            for e in entries:
                dt = datetime.fromtimestamp(e['created_at']).strftime('%H:%M')
                cats = e['cats'] or '(no category)'
                desc = (e['description'] or '')[:50].replace('\n', ' ')
                current_ui.print_line(f"   {dt}  {cats}")
                if desc:
                    current_ui.print_line(f"         {desc}")
