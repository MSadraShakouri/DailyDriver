import os
import time
from datetime import datetime, timedelta
from database import init_db, get_connection
from utils import today_jalali, format_jalali
from prayer import log_prayer, PRAYER_SLOTS
from prayer import log_prayer, log_rq, log_mp
from sleep import log_sleep
from logger import log_free_text
from view import view_entries
from birthday import add_birthday

def clear():
    os.system('clear')

def draw_header():
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()
    formatted = format_jalali(today)

    # Prayer status (same as before)
    prayer_lines = []
    for slot in PRAYER_SLOTS:
        row = cur.execute(
            "SELECT status FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
            (slot, today)
        ).fetchone()
        if row:
            icon = '✅' if row['status']=='on_time' else ('🕯️' if row['status']=='qada' else '❌')
        else:
            icon = '⏳'
        prayer_lines.append(f"{slot.replace('_',' ').title()}: {icon}")
    fajr_time = "4:30"
    prayer_str = f"🕌 Fajr {fajr_time} {prayer_lines[0]}   {prayer_lines[1]}   {prayer_lines[2]}"

    # Sleep
    sleep_row = cur.execute(
        "SELECT duration_minutes FROM sleep_logs WHERE jalali_date=?", (today,)
    ).fetchone()
    sleep_str = f"💤 Sleep: {sleep_row['duration_minutes']//60}h {sleep_row['duration_minutes']%60}m" if sleep_row else "💤 Sleep: —"

    # Birthdays (next 7 days)
    import jdatetime
    today_j = jdatetime.date.today()
    bday_lines = []
    for i in range(7):
        check_date = today_j + jdatetime.timedelta(days=i)
        m, d = check_date.month, check_date.day
        # get all birthdays with that month/day
        cur.execute("SELECT name, year FROM birthdays WHERE month=? AND day=?", (m, d))
        for row in cur.fetchall():
            age = ""
            if row['year']:
                age = f" ({check_date.year - row['year']})"
            days_away = i
            prefix = "🎂" if days_away == 0 else f"🎈{days_away}d"
            bday_lines.append(f"{prefix} {row['name']}{age}")
    bday_str = "   ".join(bday_lines[:3])  # show up to 3

    # Hygiene nudges (placeholder for now)
    hygiene_str = ""

    # Build header
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
    multi_buf = []          # holds lines if in multi-line mode
    collecting = False      # True when we are inside a :m block

    while True:
        clear()
        draw_header()

        if collecting:
            # show what we have so far
            for line in multi_buf:
                print(f"... {line}")
            line = input("... ").strip()
        else:
            line = input("> ").strip()

        if line == '':
            continue

        # --- multi-line sentinel ---
        if line == '---':
            if collecting:
                full_text = '\n'.join(multi_buf)
                log_free_text(full_text)
                multi_buf = []
                collecting = False
                input("Press Enter to continue.")
            else:
                # '---' alone in normal mode does nothing (ignored)
                pass
            continue

        # --- start multi-line ---
        if line.lower() == ':m':
            collecting = True
            multi_buf = []
            continue

        # --- while collecting, just append lines ---
        if collecting:
            multi_buf.append(line)
            continue

        # --- normal single-line commands ---
        parts = line.split()
        first = parts[0].lower()

        if first == 'q':
            print("Goodbye.")
            break
        elif first == 'p':
            log_prayer(line)
            input("Press Enter to continue.")
        elif first == 'rq':
            log_rq()
            input("Press Enter to continue.")
        elif first == 'mp':
            log_mp()
            input("Press Enter to continue.")
        elif first == 's':
            log_sleep(line)
            input("Press Enter to continue.")
        elif first == 'view':
            view_entries()   # we'll create this next
            input("Press Enter to continue.")
        elif first == '?':
            print("Commands: P S RQ MP BD T view :m ? q")
            print(":m starts multi-line entry. Finish with ---.")
            input("Press Enter to continue.")
        elif first == 'bd':
            add_birthday(line)
            input("Press Enter to continue.")
        elif first == 't':
            print("T not implemented yet.")
            input("Press Enter to continue.")
        else:
            # free text – single line
            log_free_text(line)
            input("Press Enter to continue.")

if __name__ == "__main__":
    repl()
