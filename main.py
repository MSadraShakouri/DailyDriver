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
from hygiene import manage_hygiene
from intention import add_intention
from stats import show_stats
from today import show_today
import display

def clear():
    os.system('clear')

def draw_header():
    conn = get_connection()
    cur = conn.cursor()
    today = today_jalali()
    formatted = format_jalali(today)

    # --- prayer status (single line with abbreviations) ---
    slot_labels = {'fajr': 'F', 'dhuhr_asr': 'DA', 'maghrib_isha': 'MI'}
    prayer_parts = []
    for slot in PRAYER_SLOTS:
        row = cur.execute(
            "SELECT prayer_time FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
            (slot, today)
        ).fetchone()
        if row and row['prayer_time']:
            from datetime import datetime
            dt = datetime.fromtimestamp(row['prayer_time'])
            time_str = dt.strftime('%H:%M')
            prayer_parts.append(f"{slot_labels[slot]} {time_str}")
        else:
            prayer_parts.append(f"{slot_labels[slot]} —")
    prayer_str = "   ".join(prayer_parts)   # single line

    # --- sleep ---
    sleep_row = cur.execute(
        "SELECT duration_minutes FROM sleep_logs WHERE jalali_date=?", (today,)
    ).fetchone()
    sleep_str = f"💤 Sleep: {sleep_row['duration_minutes']//60}h {sleep_row['duration_minutes']%60}m" if sleep_row else "💤 Sleep: —"

    # --- birthdays (next 7 days) ---
    import jdatetime
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
            days_away = i
            prefix = "🎂" if days_away == 0 else f"🎈{days_away}d"
            bday_lines.append(f"{prefix} {row['name']}{age}")
    bday_str = "   ".join(bday_lines[:3])

    # --- hygiene nudges ---
    cur.execute("SELECT item, desired_interval_days FROM hygiene_config")
    hygiene_items = cur.fetchall()
    nudge_lines = []
    for item_row in hygiene_items:
        item = item_row['item']
        desired = item_row['desired_interval_days']
        # Look for the last entry whose category ends with /item
        cur.execute('''
            SELECT MAX(e.started_at) as last_time
            FROM entries e
            JOIN entry_categories ec ON e.id = ec.entry_id
            JOIN categories c ON ec.category_id = c.id
            WHERE c.path LIKE ?
        ''', ('%/' + item,))
        last = cur.fetchone()
        if last and last['last_time']:
            last_ts = last['last_time']
            days_since = (int(time.time()) - last_ts) // 86400
        else:
            days_since = None

        # Early warning thresholds
        if desired >= 15:
            early = 3
        elif desired >= 7:
            early = 2
        elif desired >= 2:
            early = 1
        else:
            early = 0

        if days_since is not None and desired > 0:
            due_in = desired - days_since
            if 0 < due_in <= early:
                nudge_lines.append(f"⚠️ {item}: due in {due_in}d (last {days_since}d ago)")
            elif days_since >= desired:
                nudge_lines.append(f"⚠️ {item}: overdue! (last {days_since}d ago)")
    hygiene_str = "   ".join(nudge_lines[:2])

    # --- assemble header data ---
    display.print_header(
        date_str=formatted,
        prayer_str=prayer_str,
        sleep_str=sleep_str,
        bday_str=bday_str,
        hygiene_str=hygiene_str
    )
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
            if len(parts) > 1:
                view_entries(category_filter=parts[1])
            else:
                view_entries()
            input("Press Enter to continue.")
        elif first == '?':
            print("Commands: P S RQ MP BD T hygiene view :m ? q")
            print(":m starts multi-line entry. Finish with ---.")
            input("Press Enter to continue.")
        elif first == 'bd':
            add_birthday(line)
            input("Press Enter to continue.")
        elif first == 'hygiene':
            manage_hygiene()
            input("Press Enter to continue.")
        elif first == 't':
            add_intention(line)
            input("Press Enter to continue.")
        elif first == 'stats':
            show_stats()
            input("Press Enter to continue.")
        elif first == 'today':
            show_today()
            input("Press Enter to continue.")
        else:
            # free text – single line
            log_free_text(line)
            input("Press Enter to continue.")

if __name__ == "__main__":
    repl()
