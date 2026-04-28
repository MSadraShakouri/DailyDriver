# dailydriver/domains/prayer_log.py
import time
from datetime import datetime, timedelta
from dailydriver.core.database import get_connection_cm
from dailydriver.utils.time_utils import today_jalali
from dailydriver.domains.prayer_core import current_slot, PRAYER_SLOTS
from ui import current_ui

def log_prayer(cmd: str):
    with get_connection_cm() as conn:
        cur = conn.cursor()
        today = today_jalali()

        parts = cmd.strip().split()
        args = parts[1:] if len(parts) > 1 else []

        offset_min = None
        explicit_time = None
        jamaat_location = None
        shak_count = 0

        i = 0
        while i < len(args):
            a = args[i]
            if a.startswith('-'):
                try:
                    offset_min = int(a[1:])
                except ValueError:
                    current_ui.print_line("Invalid offset.")
                    return None
                i += 1
            elif a.lower() == 'j':
                if i+1 < len(args) and not args[i+1].startswith('-') and args[i+1].lower() not in ('j','s'):
                    jamaat_location = args[i+1]
                    i += 2
                else:
                    jamaat_location = ''
                    i += 1
            elif a.lower() == 's':
                if i+1 < len(args):
                    try:
                        shak_count = int(args[i+1])
                        i += 2
                    except ValueError:
                        shak_count = 0
                        i += 1
                else:
                    shak_count = 0
                    i += 1
            else:
                try:
                    t = datetime.strptime(a, '%H:%M')
                    explicit_time = t.hour * 60 + t.minute
                except ValueError:
                    pass
                i += 1

        if explicit_time:
            hour = explicit_time / 60
            if hour < 10:
                slot = 'fajr'
            elif hour < 17:
                slot = 'dhuhr_asr'
            else:
                slot = 'maghrib_isha'
        else:
            slot = current_slot()

        if explicit_time:
            prayer_dt = datetime.now().replace(hour=explicit_time // 60,
                                               minute=explicit_time % 60,
                                               second=0, microsecond=0)
        elif offset_min is not None:
            prayer_dt = datetime.now() - timedelta(minutes=offset_min)
        else:
            prayer_dt = datetime.now()

        time_str = prayer_dt.strftime('%H:%M')
        slot_display = slot.replace('_', ' & ').title()

        flag_parts = []
        if jamaat_location is not None:
            loc_display = jamaat_location if jamaat_location else 'yes'
            flag_parts.append(f"Jamaat ({loc_display})")
        if shak_count > 0:
            flag_parts.append(f"Shak ({shak_count})")
        extra = ", ".join(flag_parts)

        message = f"{slot_display} at {time_str}"
        if extra:
            message += f" [{extra}]"
        message += "?"

        if not current_ui.confirm(message):
            return None

        cur.execute("SELECT id, prayer_time FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
                    (slot, today))
        existing = cur.fetchone()
        if existing:
            old_time = datetime.fromtimestamp(existing['prayer_time']).strftime('%H:%M')
            confirm_replace = current_ui.confirm(
                f"⚠️  Already logged at {old_time}. Overwrite? (Enter=yes, n=cancel): ",
                default_yes=True
            )
            if not confirm_replace:
                return None
            cur.execute("DELETE FROM prayer_logs WHERE id=?", (existing['id'],))

        cur.execute(
            """INSERT INTO prayer_logs
               (prayer_slot, jalali_date, status, logged_at, prayer_time,
                jamaat_location, shak_count)
               VALUES (?,?,?,?,?,?,?)""",
            (slot, today, 'on_time', int(time.time()), int(prayer_dt.timestamp()),
             jamaat_location, shak_count)
        )
        conn.commit()

    result = f"Logged: {slot_display}\nTime:   {time_str}"
    if jamaat_location is not None:
        result += f"\nJamaat: {jamaat_location if jamaat_location else 'yes'}"
    if shak_count:
        result += f"\nShak:   {shak_count}"
    return result
