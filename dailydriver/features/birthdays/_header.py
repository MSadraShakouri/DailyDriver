# dailydriver/features/birthdays/_header.py
"""Unified birthday lines – advance reminders and today's display."""

import jdatetime

BIRTHDAY_SCHEDULE = {
    0: [14, 7, 3, 2, 1, 0],
    1: [28, 21, 14, 7, 3, 2, 1, 0],
}


def get_birthday_lines(conn, target_date):
    """Return a list of birthday display/reminder lines, sorted by days remaining.
    Uses the BIRTHDAY_SCHEDULE and the remind_level column."""
    cur = conn.cursor()
    cur.execute("SELECT name, year, month, day, remind_level FROM birthdays")
    rows = cur.fetchall()

    results = []  # (days_until, line)
    for row in rows:
        # find the next birthday date
        bday_j = jdatetime.date(target_date.year, row["month"], row["day"])
        if bday_j < target_date:
            bday_j = jdatetime.date(target_date.year + 1, row["month"], row["day"])
        days_until = (bday_j - target_date).days

        schedule = BIRTHDAY_SCHEDULE.get(row["remind_level"], [])
        if days_until not in schedule:
            continue

        # build age string
        age_str = ""
        if row["year"]:
            age = bday_j.year - row["year"]
            age_str = f" · {age}"

        if days_until == 0:
            line = f"🎂 {row['name']}{age_str}"
        elif days_until == 1:
            line = f"🎈 {row['name']} tomorrow"
        else:
            line = f"🎈 {row['name']} in {days_until} days"
        results.append((days_until, line))

    # sort by days_until ascending (today first)
    results.sort(key=lambda x: x[0])
    return [line for _, line in results]
