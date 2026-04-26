import re
from database import get_connection
from database import commit_and_update
from utils import today_jalali

def add_birthday(cmd: str):
    parts = cmd.strip().split()
    if len(parts) == 1:
        # interactive
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
        # Try full date first: YYYY/MM/DD or YYYY/M/D
        date_match = re.search(r'(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})', text)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            day = int(date_match.group(3))
            name = text[:date_match.start()].strip()
        else:
            # Try short date: MM/DD or M/D
            short_match = re.search(r'(\d{1,2})\s*/\s*(\d{1,2})', text)
            if short_match:
                month = int(short_match.group(1))
                day = int(short_match.group(2))
                year = None
                name = text[:short_match.start()].strip()
            else:
                # No date found – treat all as name, prompt for date
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
    commit_and_update(conn)
    conn.close()

    result = f"Birthday added: {name}"
    if year:
        result += f" ({year}/{month:02d}/{day:02d})"
    else:
        result += f" (????/{month:02d}/{day:02d})"
    return result
