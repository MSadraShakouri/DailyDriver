"""Interactive targets manager loop."""

from dailydriver.display.display_utils import get_width, spread_line
from dailydriver.display.header import build_header_data
from dailydriver.display.header_renderer import print_header
from dailydriver.ui.terminal_ui import current_ui

from . import actions, entries, forms, table


def show_manager(kind: str | None = None):
    while True:
        current_ui.clear()
        # Show header like qada
        data = build_header_data()
        print_header(data)

        entry_rows = entries.get_all_entries(kind=kind)
        if not entry_rows:
            current_ui.print_line("  No entries found.")
            current_ui.print_line()
            current_ui.print_line("  (a)dd  (q)uit")
            choice = current_ui.prompt("> ").strip().lower()
            if choice == "a":
                forms.add_entry(kind)
            elif choice == "q":
                break
            continue

        table.render_entries(entry_rows)

        current_ui.print_line()  # breather before commands
        _print_commands()

        current_ui.print_line()
        choice = current_ui.prompt("> ").strip().lower()

        if choice == "q":
            break
        elif choice == "?":
            _show_help()
            current_ui.prompt("Press Enter to continue.")
        elif choice == "a":
            forms.add_entry(kind)
        elif choice.startswith("l "):
            actions.log_progress(choice, kind)
        elif choice.startswith("dt "):
            actions.set_daily_total(choice, kind)
        elif choice.startswith("ct "):
            actions.set_counter_total(choice, kind)
        elif choice.startswith("cr "):
            actions.reset_counter(choice, kind)
        elif choice.startswith("p "):
            actions.toggle_pause(choice)
        elif choice.startswith("e "):
            forms.edit_entry(choice)
        elif choice.startswith("d "):
            forms.delete_entry(choice)
        else:
            current_ui.print_line("Unknown command. Type ? for help.")
            current_ui.prompt("Press Enter to continue.")


def _print_commands():
    """Print the command guide using spread_line."""
    tw = get_width()

    line1 = spread_line(["l <#> <amount> log", "e <#> edit"], width=tw, margins=1 / 8)
    current_ui.print_line(line1)

    line2 = spread_line(["dt <#> <total> daily", "d <#> delete"], width=tw, margins=1 / 8)
    current_ui.print_line(line2)

    line3 = spread_line(["ct <#> <value> counter", "a add"], width=tw, margins=1 / 8)
    current_ui.print_line(line3)

    line4 = spread_line(["cr <#> reset", "? help"], width=tw, margins=1 / 8)
    current_ui.print_line(line4)

    line5 = spread_line(["p <#> pause/unpause", "q quit"], width=tw, margins=1 / 8)
    current_ui.print_line(line5)


def _show_help():
    """Show help screen inside the manager."""
    current_ui.print_line("\n┌─ Targets Manager Help ─────────────────────────┐")
    current_ui.print_line("│ l <#> <amount>  - Log progress for entry #      │")
    current_ui.print_line("│ p <#>           - Pause/unpause entry #         │")
    current_ui.print_line("│ e <#>           - Edit entry #                  │")
    current_ui.print_line("│ d <#>           - Delete entry #                │")
    current_ui.print_line("│ a               - Add new entry                 │")
    current_ui.print_line("│ ?               - Show this help                │")
    current_ui.print_line("│ q               - Quit manager                  │")
    current_ui.print_line("└─────────────────────────────────────────────────┘")
