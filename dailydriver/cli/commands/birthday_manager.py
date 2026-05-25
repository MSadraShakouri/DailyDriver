# dailydriver/cli/commands/birthday_manager.py
"""Interactive birthday manager – list, toggle level, add, delete."""

from dailydriver.core.database import get_connection_cm
from dailydriver.domains.birthday import add_birthday
from dailydriver.ui.terminal_ui import current_ui

__all__ = ["manage_birthdays"]


def manage_birthdays():
    with get_connection_cm() as conn:
        cur = conn.cursor()
        while True:
            cur.execute(
                "SELECT id, name, month, day, year, remind_level FROM birthdays ORDER BY month, day"
            )
            rows = cur.fetchall()

            current_ui.clear()
            current_ui.print_line("─── Birthdays ───")
            if not rows:
                current_ui.print_line("No birthdays yet.")
            else:
                # Header
                current_ui.print_line(f"{'ID':<4} {'Name':<25} {'Date':<15} {'Level'}")
                current_ui.print_line("-" * 50)
                for r in rows:
                    date_str = f"{r['year'] or '????'}/{r['month']:02d}/{r['day']:02d}"
                    level_str = f"{r['remind_level']} ({'important' if r['remind_level'] == 1 else 'default'})"
                    current_ui.print_line(
                        f"{r['id']:<4} {r['name']:<25} {date_str:<15} {level_str}"
                    )

            current_ui.print_line("\n(t)oggle <id>  (a)dd  (d)elete <id>  (q)uit")
            choice = current_ui.prompt("> ").strip().lower()

            if choice == "q":
                break
            elif choice.startswith("t "):
                try:
                    id = int(choice.split()[1])
                    cur.execute(
                        "SELECT id, remind_level FROM birthdays WHERE id=?", (id,)
                    )
                    row = cur.fetchone()
                    if not row:
                        current_ui.print_line("ID not found.")
                    else:
                        new_level = 1 if row["remind_level"] == 0 else 0
                        cur.execute(
                            "UPDATE birthdays SET remind_level=? WHERE id=?",
                            (new_level, id),
                        )
                        conn.commit()
                        level_name = "important" if new_level else "default"
                        current_ui.print_line(
                            f"Level toggled to {new_level} ({level_name})."
                        )
                except (ValueError, IndexError):
                    current_ui.print_line("Usage: t <id>")
            elif choice == "a":
                result = add_birthday("bd")
                if result:
                    current_ui.print_line(result)
            elif choice.startswith("d "):
                try:
                    id = int(choice.split()[1])
                    cur.execute("SELECT name FROM birthdays WHERE id=?", (id,))
                    row = cur.fetchone()
                    if not row:
                        current_ui.print_line("ID not found.")
                    else:
                        confirm = (
                            current_ui.prompt(f"Delete {row['name']}? (y/n): ")
                            .strip()
                            .lower()
                        )
                        if confirm == "y":
                            cur.execute("DELETE FROM birthdays WHERE id=?", (id,))
                            conn.commit()
                            current_ui.print_line("Deleted.")
                        else:
                            current_ui.print_line("Cancelled.")
                except (ValueError, IndexError):
                    current_ui.print_line("Usage: d <id>")
            else:
                current_ui.print_line("Unknown command.")
            current_ui.prompt("Press Enter to continue.")
