import re
import textwrap

from dailydriver.core.database import get_connection_cm
from dailydriver.display.display_utils import display_width, get_width
from dailydriver.ui.terminal_ui import current_ui


def add_birthday(cmd: str):
    parts = cmd.strip().split()
    remind_level = 0  # default

    if len(parts) == 1:
        # interactive
        name = current_ui.prompt("Name: ").strip()
        if not name:
            return None
        day = current_ui.prompt("Day (1-31): ").strip()
        month = current_ui.prompt("Month (1-12): ").strip()
        year = current_ui.prompt("Year (e.g., 1386, Enter=skip): ").strip()
        remind_str = current_ui.prompt("Reminder level? (0=default, 1=important, Enter=0): ").strip()
        try:
            day = int(day)
            month = int(month)
            year = int(year) if year else None
            if remind_str:
                remind_level = int(remind_str)
        except ValueError:
            current_ui.print_line("Invalid numbers.")
            return None
    else:
        text = " ".join(parts[1:])
        # Check if the last token is a numeric level (0 or 1)
        tokens = text.strip().split()
        if tokens and tokens[-1].isdigit() and int(tokens[-1]) in (0, 1):
            remind_level = int(tokens[-1])
            text = " ".join(tokens[:-1])  # remove the level token from the name/date part

        # Try full date first: YYYY/MM/DD or YYYY/M/D
        date_match = re.search(r"(\d{4})\s*/\s*(\d{1,2})\s*/\s*(\d{1,2})", text)
        if date_match:
            year = int(date_match.group(1))
            month = int(date_match.group(2))
            day = int(date_match.group(3))
            name = text[: date_match.start()].strip()
        else:
            # Try short date: MM/DD or M/D
            short_match = re.search(r"(\d{1,2})\s*/\s*(\d{1,2})", text)
            if short_match:
                month = int(short_match.group(1))
                day = int(short_match.group(2))
                year = None
                name = text[: short_match.start()].strip()
            else:
                # No date found – treat all as name, prompt for date
                name = text.strip()
                if not name:
                    current_ui.print_line("No name given.")
                    return None
                day = current_ui.prompt("Day (1-31): ").strip()
                month = current_ui.prompt("Month (1-12): ").strip()
                year = current_ui.prompt("Year (Enter=skip): ").strip()
                try:
                    day = int(day)
                    month = int(month)
                    year = int(year) if year else None
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
        result += f" [important]"
    return result


def _word_wrap(text: str, width: int) -> list[str]:
    """Wrap *text* at word boundaries, returning a list of lines."""
    return textwrap.wrap(text, width=width, break_on_hyphens=False)


def manage_birthdays():
    with get_connection_cm() as conn:
        cur = conn.cursor()
        while True:
            cur.execute("SELECT id, name, month, day, year, remind_level FROM birthdays ORDER BY month, day")
            rows = cur.fetchall()

            current_ui.clear()
            current_ui.print_line("─── Birthdays ───")

            if not rows:
                current_ui.print_line("No birthdays yet.")
                current_ui.print_line("\n(a)dd  (q)uit")
                choice = current_ui.prompt("> ").strip().lower()
                if choice == "q":
                    break
                elif choice == "a":
                    result = add_birthday("bd")
                    if result:
                        current_ui.print_line(result)
                    current_ui.prompt("Press Enter to continue.")
                else:
                    current_ui.prompt("Press Enter to continue.")
                continue

            # Legend
            current_ui.print_line("0 = default (14d)   1 = important (28d)\n")

            # Dynamic column widths
            tw = get_width()
            max_id_width = max((len(str(r["id"])) for r in rows), default=2)
            max_id_width = max(max_id_width, 2)  # at least 2
            date_width = 10  # YYYY/MM/DD
            #  ID  (2 spaces)  Name  (2 spaces)  Date  (2 spaces)  Lv
            # name column gets the remaining space
            name_width = tw - max_id_width - date_width - 8
            if name_width < 5:
                name_width = 5  # absolute minimum; we trust the user's terminal

            # Header (not strictly necessary but helps)
            hdr = f"{'ID':>{max_id_width}}  {'Name':<{name_width}}  {'Date':<{date_width}}  {'Lv':>2}"
            current_ui.print_line(hdr)

            for r in rows:
                id_str = str(r["id"])
                name = r["name"]
                date_str = f"{r['year'] or '????'}/{r['month']:02d}/{r['day']:02d}"
                level_str = str(r["remind_level"])

                # Wrap name at word boundaries
                name_lines = _word_wrap(name, name_width)
                first_name_line = name_lines[0] if name_lines else ""
                rest_name_lines = name_lines[1:] if len(name_lines) > 1 else []

                # First line
                line = (
                    f"{id_str:>{max_id_width}}  {first_name_line:<{name_width}}  {date_str:<{date_width}}  {level_str}"
                )
                current_ui.print_line(line)

                # Continuation lines – only the name, indented to the name column
                indent = " " * (max_id_width + 2)
                for extra in rest_name_lines:
                    current_ui.print_line(f"{indent}{extra}")

            # Command prompt
            current_ui.print_line("\n(t)oggle <id>  (a)dd  (d)elete <id>  (q)uit")
            choice = current_ui.prompt("> ").strip().lower()

            if choice == "q":
                break
            elif choice.startswith("t "):
                try:
                    bid = int(choice.split()[1])
                    cur.execute("SELECT id, remind_level FROM birthdays WHERE id=?", (bid,))
                    row = cur.fetchone()
                    if not row:
                        current_ui.print_line("ID not found.")
                    else:
                        new_level = 1 if row["remind_level"] == 0 else 0
                        cur.execute(
                            "UPDATE birthdays SET remind_level=? WHERE id=?",
                            (new_level, bid),
                        )
                        conn.commit()
                        level_name = "important" if new_level else "default"
                        current_ui.print_line(f"Level toggled to {new_level} ({level_name}).")
                except (ValueError, IndexError):
                    current_ui.print_line("Usage: t <id>")
            elif choice == "a":
                result = add_birthday("bd")
                if result:
                    current_ui.print_line(result)
            elif choice.startswith("d "):
                try:
                    bid = int(choice.split()[1])
                    cur.execute("SELECT name FROM birthdays WHERE id=?", (bid,))
                    row = cur.fetchone()
                    if not row:
                        current_ui.print_line("ID not found.")
                    else:
                        confirm = current_ui.prompt(f"Delete {row['name']}? (y/n): ").strip().lower()
                        if confirm == "y":
                            cur.execute("DELETE FROM birthdays WHERE id=?", (bid,))
                            conn.commit()
                            current_ui.print_line("Deleted.")
                        else:
                            current_ui.print_line("Cancelled.")
                except (ValueError, IndexError):
                    current_ui.print_line("Usage: d <id>")
            else:
                current_ui.print_line("Unknown command.")
            current_ui.prompt("Press Enter to continue.")
