# DailyDriver/prayer.py
import time
from datetime import datetime, timedelta
import jdatetime
from database import get_connection
from database import commit_and_update
from utils import today_jalali

# Fixed prayer times (24h) – you can adjust later
PRAYER_TIMES = {
    'fajr': 4.5,          # 4:30
    'dhuhr_asr': 13.0,    # 13:00
    'maghrib_isha': 19.5, # 19:30
}

PRAYER_SLOTS = ['fajr', 'dhuhr_asr', 'maghrib_isha']


def current_slot() -> str:
    """Guess which prayer slot is most recent based on current time."""
    now = datetime.now().hour + datetime.now().minute / 60.0
    if now < PRAYER_TIMES['dhuhr_asr'] - 1:  # before ~12:00
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
        d += timedelta(days=1)

    missing = []
    for date_str in all_dates:
        for slot in slots:
            cur.execute("SELECT id FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?", (slot, date_str))
            if not cur.fetchone():
                missing.append((date_str, slot))

    missing_sorted = sorted(missing, key=lambda x: x[0], reverse=True)[:20]
    return missing_sorted


def log_prayer(cmd: str):
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()

    # Parse arguments: optional offset/time and flags j/s
    parts = cmd.strip().split()
    # Remove the 'p' / 'P' itself
    args = parts[1:] if len(parts) > 1 else []

    offset_min = 0
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
                print("Invalid offset.")
                conn.close()
                return None
            i += 1
        elif a.lower() == 'j':
            # next argument is the location (optional)
            if i+1 < len(args) and not args[i+1].startswith('-') and args[i+1].lower() not in ('j','s'):
                jamaat_location = args[i+1]
                i += 2
            else:
                jamaat_location = ''   # just 'j' means congregation, location empty
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
            # assume time
            try:
                t = datetime.strptime(a, '%H:%M')
                explicit_time = t.hour * 60 + t.minute
            except ValueError:
                pass
            i += 1

    # Determine slot
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

    # Compute prayer datetime
    if explicit_time:
        prayer_dt = datetime.now().replace(hour=explicit_time // 60,
                                           minute=explicit_time % 60,
                                           second=0, microsecond=0)
    elif offset_min:
        prayer_dt = datetime.now() - timedelta(minutes=offset_min)
    else:
        prayer_dt = datetime.now()

    time_str = prayer_dt.strftime('%H:%M')
    slot_display = slot.replace('_', ' & ').title()

    # Show confirmation
    flag_parts = []
    if jamaat_location is not None:
        loc_display = jamaat_location if jamaat_location else 'yes'
        flag_parts.append(f"Jamaat ({loc_display})")
    if shak_count > 0:
        flag_parts.append(f"Shak ({shak_count})")
    extra = ", ".join(flag_parts)
    if extra:
        print(f"\n{slot_display} at {time_str} [{extra}]? (Enter=yes, n=cancel)")
    else:
        print(f"\n{slot_display} at {time_str}? (Enter=yes, n=cancel)")

    confirm = input("> ").strip().lower()
    if confirm != '' and confirm != 'y':
        conn.close()
        return None

    # Save
    cur.execute(
        "INSERT OR REPLACE INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time, jamaat_location, shak_count) VALUES (?,?,?,?,?,?,?)",
        (slot, today, 'on_time', int(time.time()), int(prayer_dt.timestamp()), jamaat_location, shak_count)
    )
    commit_and_update(conn)
    conn.close()

    result = f"Logged: {slot_display}\nTime:   {time_str}"
    if jamaat_location is not None:
        result += f"\nJamaat: {jamaat_location if jamaat_location else 'yes'}"
    if shak_count:
        result += f"\nShak:   {shak_count}"
    return result


def time_offset(minutes):
    return timedelta(minutes=minutes)


def log_rq():
    """Let user select an unlogged prayer slot and mark it as qada."""
    conn = get_connection()
    missing = _get_unlogged_slots(conn)

    if missing is None:
        print("No prayer logs yet – nothing to mark as qada.")
        conn.close()
        return

    if not missing:
        print("All prayer slots are logged – nothing to mark as qada.")
        conn.close()
        return

    print("\nUnlogged prayer slots (newest first):")
    for i, (date_str, slot) in enumerate(missing, 1):
        print(f"  [{i}] {date_str}  {slot}")

    choice = input("Select number to mark as qada (q=quit): ").strip()
    if choice.lower() == 'q':
        conn.close()
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(missing):
            date_str, slot = missing[idx]
            cur = conn.cursor()
            cur.execute("INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at) VALUES (?,?,?,?)",
                        (slot, date_str, 'qada', int(time.time())))
            commit_and_update(conn)
            print(f"Marked {slot} on {date_str} as qada.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")
    conn.close()


def log_mp():
    """View all unlogged prayer slots and allow marking as missed or qada."""
    conn = get_connection()
    missing = _get_unlogged_slots(conn)

    if missing is None:
        print("No prayer logs yet.")
        conn.close()
        return

    if not missing:
        print("All prayer slots are logged.")
        conn.close()
        return

    print("\nUnlogged prayer slots (newest first):")
    for i, (date_str, slot) in enumerate(missing, 1):
        print(f"  [{i}] {date_str}  {slot}")

    choice = input("Select number to mark (q=quit): ").strip()
    if choice.lower() == 'q':
        conn.close()
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(missing):
            date_str, slot = missing[idx]
            mark = input("Mark as (m)issed or (q)ada? ").strip().lower()
            if mark == 'q':
                status = 'qada'
            elif mark == 'm':
                status = 'missed'
            else:
                print("Invalid choice.")
                conn.close()
                return
            cur = conn.cursor()
            cur.execute("INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at) VALUES (?,?,?,?)",
                        (slot, date_str, status, int(time.time())))
            commit_and_update(conn)
            print(f"Marked {slot} on {date_str} as {status}.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")
    conn.close()
