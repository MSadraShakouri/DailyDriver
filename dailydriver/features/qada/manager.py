"""Interactive qada manager."""

import jdatetime

from dailydriver.display.display_utils import get_width, spread_line
from dailydriver.display.header import build_header_data
from dailydriver.display.header_renderer import print_header

from . import entries as entry_store
from . import logging, overview
from .table import render_entries
from .editor import edit_entry
from dailydriver.ui.terminal_ui import current_ui


def show_qada_manager():
    """Main loop for the qada manager."""
    while True:
        current_ui.clear()
        # Show header like hygiene
        data = build_header_data()
        print_header(data)

        entries = overview.get_all_entries_with_progress()

        # Render table (no extra blank line before it)
        render_entries(entries)

        # Command guide – two lines spread across 2/3 of screen
        current_ui.print_line()  # breather before commands
        _print_commands()

        # Breather before prompt
        current_ui.print_line()
        choice = current_ui.prompt("> ").strip().lower()

        if choice == "q":
            break
        elif choice == "?":
            _show_help()
            current_ui.prompt("Press Enter to continue.")
        elif choice.startswith("l "):
            _log_entry(choice)
        elif choice.startswith("p "):
            _pause_entry(choice)
        elif choice.startswith("e "):
            edit_entry(choice)
        else:
            current_ui.print_line("Unknown command. Type ? for help.")
            current_ui.prompt("Press Enter to continue.")


def _print_commands():
    """Print the command guide using spread_line."""
    tw = get_width()

    # Line 1: l and p
    line1_parts = ["l <#> log progress", "p <#> pause/unpause"]
    # Pad each to same width? No – spread_line handles distribution
    line1 = spread_line(line1_parts, width=tw, margins=1 / 8)
    current_ui.print_line(line1)

    # Line 2: e, ?, q
    line2_parts = ["e <#> edit", "? help", "q quit"]
    line2 = spread_line(line2_parts, width=tw, margins=1 / 8)
    current_ui.print_line(line2)


def _show_help():
    """Show help screen inside the manager."""
    current_ui.print_line("\n┌─ Qada Manager Help ───────────────────────────┐")
    current_ui.print_line("│ l <#>  - Log progress for entry #              │")
    current_ui.print_line("│ p <#>  - Pause/unpause entry #                 │")
    current_ui.print_line("│ e <#>  - Edit entry # (target/interval)        │")
    current_ui.print_line("│ ?      - Show this help                        │")
    current_ui.print_line("│ q      - Quit manager                          │")
    current_ui.print_line("└─────────────────────────────────────────────────┘")










def _log_entry(choice):
    """Log progress for an entry."""
    parts = choice.split()
    if len(parts) < 2:
        current_ui.print_line("Usage: l <#>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        idx = int(parts[1])
    except ValueError:
        current_ui.print_line("Invalid number.")
        current_ui.prompt("Press Enter to continue.")
        return

    entries = overview.get_all_entries_with_progress()
    if idx < 1 or idx > len(entries):
        current_ui.print_line(f"Entry #{idx} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries[idx - 1]
    target = entry["target_total"]

    if target <= 0:
        current_ui.print_line("Nothing to log (target not set or complete).")
        current_ui.prompt("Press Enter to continue.")
        return

    amount_str = current_ui.prompt("Amount to log (Enter=1): ").strip()
    try:
        amount = int(amount_str) if amount_str else 1
    except ValueError:
        current_ui.print_line("Invalid number.")
        current_ui.prompt("Press Enter to continue.")
        return

    if amount <= 0:
        current_ui.print_line("Amount must be positive.")
        current_ui.prompt("Press Enter to continue.")
        return

    if entry["kind"] == "prayer":
        result = logging.log_prayer_qada(entry["id"], amount)
    else:  # fasting
        result = logging.log_fasting(entry["id"])

    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")


def _pause_entry(choice):
    """Pause or unpause an entry."""
    parts = choice.split()
    if len(parts) < 2:
        current_ui.print_line("Usage: p <#>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        idx = int(parts[1])
    except ValueError:
        current_ui.print_line("Invalid number.")
        current_ui.prompt("Press Enter to continue.")
        return

    entries = overview.get_all_entries_with_progress()
    if idx < 1 or idx > len(entries):
        current_ui.print_line(f"Entry #{idx} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries[idx - 1]
    entry_id = entry["id"]

    if entry["target_total"] == -1:
        current_ui.print_line("Entry not set. Use 'e' first.")
        current_ui.prompt("Press Enter to continue.")
        return

    if entry["is_paused"]:
        confirm = current_ui.prompt("Unpause? (y/n): ").strip().lower()
        if confirm == "y":
            entry_store.edit_entry(entry_id, paused_until=None)
            current_ui.print_line("Entry unpaused.")
        else:
            current_ui.print_line("Cancelled.")
        current_ui.prompt("Press Enter to continue.")
        return

    days_str = current_ui.prompt("Pause for N days (Enter=1): ").strip()
    try:
        days = int(days_str) if days_str else 1
    except ValueError:
        current_ui.print_line("Invalid number.")
        current_ui.prompt("Press Enter to continue.")
        return

    if days <= 0:
        current_ui.print_line("Days must be positive.")
        current_ui.prompt("Press Enter to continue.")
        return

    today = jdatetime.date.today()
    pause_until = today + jdatetime.timedelta(days=days)
    entry_store.edit_entry(entry_id, paused_until=pause_until.strftime("%Y-%m-%d"))

    current_ui.print_line(f"Paused for {days} days (until {pause_until.strftime('%Y-%m-%d')}).")
    current_ui.prompt("Press Enter to continue.")
