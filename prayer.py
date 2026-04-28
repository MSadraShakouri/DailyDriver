import time
from datetime import datetime, timedelta
import jdatetime
from dailydriver.core.database import get_connection_cm
from dailydriver.utils.time_utils import today_jalali
from ui import current_ui

# Fixed prayer times (24h)
PRAYER_TIMES = {
    'fajr': 4.5,          # 4:30
    'dhuhr_asr': 13.0,    # 13:00
    'maghrib_isha': 19.5, # 19:30
}

PRAYER_SLOTS = ['fajr', 'dhuhr_asr', 'maghrib_isha']


def current_slot() -> str:
    """Guess which prayer slot is most recent based on current time."""
    now = datetime.now().hour + datetime.now().minute / 60.0
    if now < PRAYER_TIMES['dhuhr_asr'] - 1:
        return 'fajr'
    elif now < PRAYER_TIMES['maghrib_isha'] - 1:
        return 'dhuhr_asr'
    else:
        return 'maghrib_isha'


def _get_unlogged_slots(conn):
    """
    Return a list of (jalali_date, slot) for all unlogged prayer slots
    since the first prayer log, sorted newest first, limited to 20.
    Returns None if no logs exist at all.
    """
    cur = conn.cursor()
    today = today_jalali()

    cur.execute("SELECT MIN(jalali_date) FROM prayer_logs")
    first_date = cur.fetchone()[0]
    if not first_date:
        return None

    start_y, start_m, start_d = map(int, first_date.split('-'))
    end_y, end_m, end_d = map(int, today.split('-'))
    start_j = jdatetime.date(start_y, start_m, start_d)
    end_j = jdatetime.date(end_y, end_m, end_d)

    slots = PRAYER_SLOTS
    all_dates = []
    d = start_j
    while d <= end_j:
        all_dates.append(d.strftime('%Y-%m-%d'))
        d += jdatetime.timedelta(days=1)

    missing = []
    for date_str in all_dates:
        for slot in slots:
            cur.execute("SELECT id FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?", (slot, date_str))
            if not cur.fetchone():
                missing.append((date_str, slot))

    missing_sorted = sorted(missing, key=lambda x: x[0], reverse=True)[:20]
    return missing_sorted


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
        # conn.close() no longer needed
    # The connection is automatically closed by the context manager

    result = f"Logged: {slot_display}\nTime:   {time_str}"
    if jamaat_location is not None:
        result += f"\nJamaat: {jamaat_location if jamaat_location else 'yes'}"
    if shak_count:
        result += f"\nShak:   {shak_count}"
    return result


def log_rq():
    with get_connection_cm() as conn:
        missing = _get_unlogged_slots(conn)

        if missing is None:
            current_ui.print_line("No prayer logs yet – nothing to mark as qada.")
            return

        if not missing:
            current_ui.print_line("All prayer slots are logged.")
            return

        current_ui.print_line("\nUnlogged prayer slots (newest first):")
        for i, (date_str, slot) in enumerate(missing, 1):
            current_ui.print_line(f"  [{i}] {date_str}  {slot}")

        choice = current_ui.prompt("Select number to mark as qada (q=quit): ").strip()
        if choice.lower() == 'q':
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(missing):
                date_str, slot = missing[idx]
                cur = conn.cursor()
                cur.execute("INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at) VALUES (?,?,?,?)",
                            (slot, date_str, 'qada', int(time.time())))
                conn.commit()
                current_ui.print_line(f"Marked {slot} on {date_str} as qada.")
            else:
                current_ui.print_line("Invalid selection.")
        except ValueError:
            current_ui.print_line("Invalid input.")


def log_mp():
    with get_connection_cm() as conn:
        missing = _get_unlogged_slots(conn)

        if missing is None:
            current_ui.print_line("No prayer logs yet.")
            return

        if not missing:
            current_ui.print_line("All prayer slots are logged.")
            return

        current_ui.print_line("\nUnlogged prayer slots (newest first):")
        for i, (date_str, slot) in enumerate(missing, 1):
            current_ui.print_line(f"  [{i}] {date_str}  {slot}")

        choice = current_ui.prompt("Select number to mark (q=quit): ").strip()
        if choice.lower() == 'q':
            return
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(missing):
                date_str, slot = missing[idx]
                mark = current_ui.prompt("Mark as (m)issed or (q)ada? ").strip().lower()
                if mark == 'q':
                    status = 'qada'
                elif mark == 'm':
                    status = 'missed'
                else:
                    current_ui.print_line("Invalid choice.")
                    return
                cur = conn.cursor()
                cur.execute("INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at) VALUES (?,?,?,?)",
                            (slot, date_str, status, int(time.time())))
                conn.commit()
                current_ui.print_line(f"Marked {slot} on {date_str} as {status}.")
            else:
                current_ui.print_line("Invalid selection.")
        except ValueError:
            current_ui.print_line("Invalid input.")
