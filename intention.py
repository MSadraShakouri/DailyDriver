import time
from database import get_connection

def add_intention(cmd: str):
    """
    T "description"  → adds intention with description only.
    T                → interactive prompts for description, deadline, expected duration.
    """
    parts = cmd.strip().split(maxsplit=1)
    if len(parts) > 1:
        description = parts[1]
        deadline = None
        expected = None
    else:
        description = input("Description: ").strip()
        if not description:
            print("Cancelled.")
            return
        deadline_str = input("Deadline (Jalali YYYY/MM/DD, or leave empty): ").strip()
        if deadline_str:
            # simple conversion to unix timestamp (noon that day)
            try:
                import jdatetime
                y, m, d = map(int, deadline_str.split('/'))
                jdate = jdatetime.date(y, m, d)
                gdate = jdate.togregorian()
                from datetime import datetime
                deadline = int(datetime(gdate.year, gdate.month, gdate.day, 12, 0).timestamp())
            except:
                print("Invalid date format. Ignoring deadline.")
                deadline = None
        else:
            deadline = None

        expected_str = input("Expected duration (minutes, or leave empty): ").strip()
        if expected_str:
            try:
                expected = int(expected_str)
            except ValueError:
                print("Invalid number. Ignoring.")
                expected = None
        else:
            expected = None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO intentions (description, deadline, expected_duration_minutes) VALUES (?,?,?)",
        (description, deadline, expected)
    )
    conn.commit()
    conn.close()
    print("Intention added.")
