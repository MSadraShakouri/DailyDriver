import os
import time
from datetime import datetime, timedelta
from database import init_db, get_connection
from utils import today_jalali, format_jalali
from prayer import log_prayer, PRAYER_SLOTS
from sleep import log_sleep
from logger import log_free_text

def clear():
    os.system('clear')

def draw_header():
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()
    formatted = format_jalali(today)

    # prayer statuses
    prayer_lines = []
    for slot in PRAYER_SLOTS:
        row = cur.execute(
            "SELECT status FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
            (slot, today)
        ).fetchone()
        if row:
            if row['status'] == 'on_time':
                icon = '✅'
            elif row['status'] == 'qada':
                icon = '🕯️'
            else:
                icon = '❌'
        else:
            icon = '⏳'
        prayer_lines.append(f"{slot.replace('_',' ').title()}: {icon}")
    # Fajr time displayed
    fajr_time = "4:30"  # hardcoded for now
    prayer_str = f"🕌 Fajr {fajr_time} {prayer_lines[0]}   {prayer_lines[1]}   {prayer_lines[2]}"

    # sleep
    sleep_row = cur.execute(
        "SELECT duration_minutes FROM sleep_logs WHERE jalali_date=?",
        (today,)
    ).fetchone()
    if sleep_row:
        mins = sleep_row['duration_minutes']
        sleep_str = f"💤 Sleep: {mins//60}h {mins%60}m"
    else:
        sleep_str = "💤 Sleep: —"

    # birthdays (next 7 days)
    bday_str = ""
    # We'll compute Jalali dates and compare; to keep it simple, we'll leave this blank for now.
    # We'll implement later.

    # hygiene nudges – placeholder
    hygiene_str = ""

    # Build header lines
    header = f"════════ {formatted} ════════\n"
    header += f"{prayer_str}\n"
    header += f"{sleep_str}\n"
    if bday_str:
        header += f"{bday_str}\n"
    if hygiene_str:
        header += f"{hygiene_str}\n"
    header += "────────────────────────────────────\n"
    print(header, end='')
    conn.close()

def repl():
    init_db()
    while True:
        clear()
        draw_header()
        line = input("> ").strip()
        if line == '':
            continue
        parts = line.split()
        first = parts[0].lower()

        if first == 'q':
            print("Goodbye.")
            break
        elif first == 'p':
            log_prayer(line)
        elif first == 's':
            log_sleep(line)
        elif first == '?':
            print("Commands: P S RQ MP BD T view ? q")
            print("Free text: just type your entry (single line for now).")
            input("Press Enter to continue.")
        elif first in ('rq', 'mp', 'bd', 't', 'view'):
            print(f"{first} not implemented yet.")
            input("Press Enter to continue.")
        else:
            log_free_text(line)
            input("Press Enter to continue.")

if __name__ == "__main__":
    repl()
