import time
import jdatetime
from datetime import datetime
from dailydriver.core.database import get_connection_cm, get_last_hygiene_time
from dailydriver.utils.time_utils import today_jalali, format_jalali
from dailydriver.core.logger import get_pending_start, get_active_great_event
from ui import current_ui

def build_header_data():
    """Collect all data needed for the daily header and return a dict."""
    with get_connection_cm() as conn:
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
        cur.execute("SELECT id, item, desired_interval_days, early_warning_enabled, show_due_today FROM hygiene_config ORDER BY item")
        hygiene_items = cur.fetchall()
        nudge_lines = []
        now_ts = int(time.time())
        for item_row in hygiene_items:
            item = item_row['item']
            desired = item_row['desired_interval_days']
            early_enabled = item_row['early_warning_enabled']
            due_today_enabled = item_row['show_due_today']

            last_time = get_last_hygiene_time(conn, item)
            days_since = (now_ts - last_time) // 86400 if last_time else None

            if days_since is None:
                continue

            # Early warning thresholds (hardcoded)
            if desired >= 15:
                early_threshold = 3
            elif desired >= 7:
                early_threshold = 2
            elif desired >= 2:
                early_threshold = 1
            else:
                early_threshold = 0

            # 1. Overdue (always show)
            if days_since > desired:
                nudge_lines.append(f"⚠️ {item}: overdue! (last {days_since}d ago)")

            # 2. Due today (optional)
            elif days_since == desired and due_today_enabled:
                nudge_lines.append(f"⚠️ {item}: due today")

            # 3. Early warning (optional)
            elif days_since < desired and early_enabled and early_threshold > 0:
                remaining = desired - days_since
                if remaining <= early_threshold:
                    nudge_lines.append(f"⚠️ {item}: due in {remaining}d (last {days_since}d ago)")

        hygiene_str = "   ".join(nudge_lines[:2])

        # ---------- great event indicator ----------
        great_event_str = ''
        active_ge = get_active_great_event()
        if active_ge:
            start_ts, cats = active_ge
            from datetime import datetime as dt   # already imported as datetime
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
            'event_str': event_str,
            'great_event_str': great_event_str,
            'last_entry_time': last_entry_time,
        }
