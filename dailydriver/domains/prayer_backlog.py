# dailydriver/domains/prayer_backlog.py
import time
import jdatetime
from dailydriver.core.database import get_connection_cm
from dailydriver.utils.time_utils import today_jalali
from dailydriver.domains.prayer_core import PRAYER_SLOTS
from dailydriver.ui.terminal_ui import current_ui

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
