import time
from database import get_connection
from database import commit_and_update

def add_intention(cmd: str):
    """
    T "description"  → adds intention with description only.
    T                → interactive prompts.
    Returns a result string or None.
    """
    parts = cmd.strip().split(maxsplit=1)
    if len(parts) > 1:
        description = parts[1]
        deadline = None
        expected = None
    else:
        description = input("Description: ").strip()
        if not description:
            return None
        deadline_str = input("Deadline (Jalali YYYY/MM/DD, or Enter=skip): ").strip()
        if deadline_str:
            try:
                import jdatetime
                y, m, d = map(int, deadline_str.split('/'))
                jdate = jdatetime.date(y, m, d)
                gdate = jdate.togregorian()
                from datetime import datetime
                deadline = int(datetime(gdate.year, gdate.month, gdate.day, 12, 0).timestamp())
            except:
                print("Invalid date. Ignoring deadline.")
                deadline = None
        else:
            deadline = None
        expected_str = input("Expected duration (min, Enter=skip): ").strip()
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
    commit_and_update(conn)
    conn.close()

    result = "Intention added:\n"
    result += f"  {description}\n"
    if deadline:
        from datetime import datetime
        result += f"  Deadline: {datetime.fromtimestamp(deadline).strftime('%Y-%m-%d %H:%M')}\n"
    if expected:
        result += f"  Expected: {expected} min"
    return result.strip()
