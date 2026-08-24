"""Birthday command handlers."""

from dailydriver.core.database import get_connection_cm
from dailydriver.ui.terminal_ui import current_ui


def add_birthday(cmd: str = ""):
    """Add a birthday through interactive prompts.

    Creation is deliberately fully interactive as of v2.0: any inline arguments
    are ignored so there is a single, validated path for entering a name, date,
    and reminder level. Routine logging stays inline elsewhere; deliberate
    creation like this benefits from prompts and validation.
    """
    name = current_ui.prompt("Name: ").strip()
    if not name:
        return None

    day_str = current_ui.prompt("Day (1-31): ").strip()
    month_str = current_ui.prompt("Month (1-12): ").strip()
    year_str = current_ui.prompt("Year (e.g., 1386, Enter=skip): ").strip()
    remind_str = current_ui.prompt("Reminder level? (0=default, 1=important, Enter=0): ").strip()

    try:
        day = int(day_str)
        month = int(month_str)
        year = int(year_str) if year_str else None
        remind_level = int(remind_str) if remind_str else 0
    except ValueError:
        current_ui.print_line("Invalid numbers.")
        return None

    if not (1 <= month <= 12 and 1 <= day <= 31):
        current_ui.print_line("Invalid date.")
        return None

    with get_connection_cm() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO birthdays (name, day, month, year, remind_level) VALUES (?,?,?,?,?)",
            (name, day, month, year, remind_level),
        )
        conn.commit()

    result = f"Birthday added: {name}"
    if year:
        result += f" ({year}/{month:02d}/{day:02d})"
    else:
        result += f" (????/{month:02d}/{day:02d})"
    if remind_level > 0:
        result += " [important]"
    return result
