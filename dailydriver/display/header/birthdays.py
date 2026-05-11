# dailydriver/display/header/birthdays.py
"""Birthday header line (next 7 days)."""
import jdatetime

def get_birthday_str(conn, target_date):
    cur = conn.cursor()
    lines = []
    for i in range(7):
        check_date = target_date + jdatetime.timedelta(days=i)
        m_day, d_day = check_date.month, check_date.day
        cur.execute("SELECT name, year FROM birthdays WHERE month=? AND day=?", (m_day, d_day))
        for row in cur.fetchall():
            age = ""
            if row['year']:
                age = f" ({check_date.year - row['year']})"
            prefix = "🎂" if i == 0 else f"🎈{i}d"
            lines.append(f"{prefix} {row['name']}{age}")
    return "   ".join(lines[:3])
