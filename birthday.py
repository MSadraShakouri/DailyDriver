import re
from database import get_connection
from utils import today_jalali

def add_birthday(cmd: str):
    """
    Parse 'BD' command.
    'BD' alone → interactive prompts.
    'BD Name Surname 1386/01/01' → inline addition.
    """
    parts = cmd.strip().split()
    if len(parts) == 1:
        # interactive
        name = input("Name: ").strip()
        if not name:
            print("Cancelled.")
            return
        day = input("Day (1-31): ").strip()
        month = input("Month (1-12): ").strip()
        year = input("Year (e.g., 1386, or leave blank): ").strip()
        try:
            day = int(day)
            month = int(month)
            year = int(year) if year else None
        except ValueError:
            print("Invalid numbers.")
            return
    else:
        # try to parse date from the end
        # look for pattern like 1386/01/01 or 1386/1/1
        text = ' '.join(parts[1:])
        date_match = re.search(r'(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})', text)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            day = int(date_match.group(3))
            name = text[:date_match.start()].strip()
            if not name:
                print("No name given.")
                return
        else:
            # no date, treat all as name, prompt for date
            name = text.strip()
            if not name:
                print("No name given.")
                return
            day = input("Day (1-31): ").strip()
            month = input("Month (1-12): ").strip()
            year = input("Year (optional): ").strip()
            try:
                day = int(day)
                month = int(month)
                year = int(year) if year else None
            except ValueError:
                print("Invalid numbers.")
                return

    # Validate ranges
    if not (1 <= month <= 12 and 1 <= day <= 31):
        print("Invalid date.")
        return

    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO birthdays (name, day, month, year) VALUES (?,?,?,?)",
        (name, day, month, year)
    )
    conn.commit()
    conn.close()
    print(f"Birthday added: {name} ({year or '????'}/{month:02d}/{day:02d})")
