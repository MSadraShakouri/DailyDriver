import time
from datetime import datetime
from database import get_connection
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

def log_prayer(cmd: str):
    """
    Parse a 'P' command, ask for slot/time confirmation, then log.
    """
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()

    parts = cmd.strip().split()
    offset_min = 0
    explicit_time = None
    if len(parts) > 1:
        arg = parts[1]
        if arg.startswith('-'):
            try:
                offset_min = int(arg[1:])
            except ValueError:
                print("Invalid offset.")
                conn.close()
                return
        else:
            try:
                t = datetime.strptime(arg, '%H:%M')
                explicit_time = t.hour * 60 + t.minute
            except ValueError:
                print("Time not understood. Use HH:MM or -15 offset.")
                conn.close()
                return

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

    # Compute prayer time (approx)
    base_time = PRAYER_TIMES.get(slot, 0)
    from datetime import timedelta
    prayer_dt = datetime.now().replace(hour=int(base_time), minute=int((base_time % 1) * 60), second=0, microsecond=0)
    if offset_min:
        prayer_dt = prayer_dt - timedelta(minutes=offset_min)
    if explicit_time:
        prayer_dt = datetime.now().replace(hour=explicit_time // 60, minute=explicit_time % 60, second=0, microsecond=0)

    time_str = prayer_dt.strftime('%H:%M')
    slot_display = slot.replace('_', ' & ').title()

    # Single confirmation line
    print(f"\n{slot_display} at {time_str}? (Enter=yes, n=cancel)")
    confirm = input("> ").strip().lower()
    if confirm != '' and confirm != 'y':
        conn.close()
        return

    # Insert
    cur.execute(
        "INSERT OR REPLACE INTO prayer_logs (prayer_slot, jalali_date, status, logged_at, prayer_time) VALUES (?,?,?,?,?)",
        (slot, today, 'on_time', int(time.time()), int(prayer_dt.timestamp()))
    )
    conn.commit()
    print(f"Logged: {slot_display}")
    conn.close()

def time_offset(minutes):
    from datetime import timedelta
    return timedelta(minutes=minutes)

def log_rq():
    """Let user select an unlogged prayer slot and mark it as qada."""
    conn = get_connection()
    cur = conn.cursor()

    # Find all prayer slots that have NO log entry (any date)
    # We'll list them grouped by date, newest first
    today = today_jalali()
    # Generate all possible (slot, date) pairs since app start?
    # For simplicity: query prayer_logs for slots that exist, then find missing.
    # Better: compare against a list of expected slots for each day since first log.
    cur.execute("SELECT MIN(jalali_date) FROM prayer_logs")
    first_date = cur.fetchone()[0]
    if not first_date:
        print("No prayer logs yet – nothing to mark as qada.")
        conn.close()
        return

    # Get all dates from first_date to today
    from datetime import timedelta
    import jdatetime
    # Convert to dates
    start_y, start_m, start_d = map(int, first_date.split('-'))
    end_y, end_m, end_d = map(int, today.split('-'))
    start_j = jdatetime.date(start_y, start_m, start_d)
    end_j = jdatetime.date(end_y, end_m, end_d)

    slots = ['fajr', 'dhuhr_asr', 'maghrib_isha']
    all_dates = []
    d = start_j
    while d <= end_j:
        all_dates.append(d.strftime('%Y-%m-%d'))
        d += timedelta(days=1)

    # For each slot and each date, check if log exists
    missing = []
    for date_str in all_dates:
        for slot in slots:
            cur.execute("SELECT id FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?", (slot, date_str))
            if not cur.fetchone():
                missing.append((date_str, slot))

    if not missing:
        print("All prayer slots are logged – nothing to mark as qada.")
        conn.close()
        return

    # Show newest first (last 20)
    missing_sorted = sorted(missing, key=lambda x: x[0], reverse=True)[:20]
    print("\nUnlogged prayer slots (newest first):")
    for i, (date_str, slot) in enumerate(missing_sorted, 1):
        print(f"  [{i}] {date_str}  {slot}")

    choice = input("Select number to mark as qada (q=quit): ").strip()
    if choice.lower() == 'q':
        conn.close()
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(missing_sorted):
            date_str, slot = missing_sorted[idx]
            cur.execute("INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at) VALUES (?,?,?,?)",
                        (slot, date_str, 'qada', int(time.time())))
            conn.commit()
            print(f"Marked {slot} on {date_str} as qada.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")
    conn.close()

def log_mp():
    """View all unlogged prayer slots and allow marking as missed or qada."""
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()

    cur.execute("SELECT MIN(jalali_date) FROM prayer_logs")
    first_date = cur.fetchone()[0]
    if not first_date:
        print("No prayer logs yet.")
        conn.close()
        return

    start_y, start_m, start_d = map(int, first_date.split('-'))
    end_y, end_m, end_d = map(int, today.split('-'))
    import jdatetime
    from datetime import timedelta
    start_j = jdatetime.date(start_y, start_m, start_d)
    end_j = jdatetime.date(end_y, end_m, end_d)

    slots = ['fajr', 'dhuhr_asr', 'maghrib_isha']
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

    if not missing:
        print("All prayer slots are logged.")
        conn.close()
        return

    missing_sorted = sorted(missing, key=lambda x: x[0], reverse=True)[:20]
    print("\nUnlogged prayer slots (newest first):")
    for i, (date_str, slot) in enumerate(missing_sorted, 1):
        print(f"  [{i}] {date_str}  {slot}")

    choice = input("Select number to mark (q=quit): ").strip()
    if choice.lower() == 'q':
        conn.close()
        return
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(missing_sorted):
            date_str, slot = missing_sorted[idx]
            mark = input("Mark as (m)issed or (q)ada? ").strip().lower()
            if mark == 'q':
                status = 'qada'
            elif mark == 'm':
                status = 'missed'
            else:
                print("Invalid choice.")
                conn.close()
                return
            cur.execute("INSERT INTO prayer_logs (prayer_slot, jalali_date, status, logged_at) VALUES (?,?,?,?)",
                        (slot, date_str, status, int(time.time())))
            conn.commit()
            print(f"Marked {slot} on {date_str} as {status}.")
        else:
            print("Invalid selection.")
    except ValueError:
        print("Invalid input.")
    conn.close()
