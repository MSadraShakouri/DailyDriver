import re
from database import get_connection
from utils import today_jalali

def add_birthday(cmd: str):
    parts = cmd.strip().split()
    if len(parts) == 1:
        name = input("Name: ").strip()
        if not name:
            return None
        day = input("Day (1-31): ").strip()
        month = input("Month (1-12): ").strip()
        year = input("Year (e.g., 1386, Enter=skip): ").strip()
        try:
            day = int(day)
            month = int(month)
            year = int(year) if year else None
        except ValueError:
            print("Invalid numbers.")
            return None
    else:
        text = ' '.join(parts[1:])
        date_match = re.search(r'(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})', text)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            day = int(date_match.group(3))
            name = text[:date_match.start()].strip()
            if not name:
                print("No name given.")
                return None
        else:
            name = text.strip()
            if not name:
                print("No name given.")
                return None
            day = input("Day (1-31): ").strip()
            month = input("Month (1-12): ").strip()
            year = input("Year (Enter=skip): ").strip()
            try:
                day = int(day)
                month = int(month)
                year = int(year) if year else None
            except ValueError:
                print("Invalid numbers.")
                return None

    if not (1 <= month <= 12 and 1 <= day <= 31):
        print("Invalid date.")
        return None

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO birthdays (name, day, month, year) VALUES (?,?,?,?)",
        (name, day, month, year)
    )
    conn.commit()
    conn.close()

    result = f"Birthday added: {name}"
    if year:
        result += f" ({year}/{month:02d}/{day:02d})"
    else:
        result += f" (????/{month:02d}/{day:02d})"
    return result
