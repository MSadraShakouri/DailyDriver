# dailydriver/display/header/birthdays.py
"""Birthday header line (next 7 days)."""

import jdatetime


def get_birthday_str(conn, target_date):
    cur = conn.cursor()
    lines = []
    for i in range(7):
        check_date = target_date + jdatetime.timedelta(days=i)
        m_day, d_day = check_date.month, check_date.day
        cur.execute(
            "SELECT name, year FROM birthdays WHERE month=? AND day=?", (m_day, d_day)
        )
        for row in cur.fetchall():
            if row["year"]:
                age = check_date.year - row["year"]
                age_str = f" · {age}"
            else:
                age_str = ""
            if i == 0:
                lines.append(f"🎂 {row['name']}{age_str}")
            else:
                lines.append(f"🎈 {row['name']} {i}d{age_str}")
    return "   ".join(lines[:3])
