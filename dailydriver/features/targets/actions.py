"""Interactive progress and pause actions for the targets manager."""

from dailydriver.ui.terminal_ui import current_ui

from . import commands, entries, progress


def log_progress(choice: str, kind: str | None = None):
    """Handle logging from the manager."""
    parts = choice.strip().split()
    if len(parts) < 3:
        current_ui.print_line("Usage: l <#> <amount>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        identifier = int(parts[1])
    except ValueError:
        current_ui.print_line("ID must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        amount = int(parts[2])
    except ValueError:
        current_ui.print_line("Amount must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    if amount <= 0:
        current_ui.print_line("Amount must be positive.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries.get_entry_by_id(identifier)
    if not entry:
        current_ui.print_line(f"Entry {identifier} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    if kind and entry["kind"] != kind:
        current_ui.print_line(f"'{entry['name']}' is a {entry['kind']}, not a {kind}.")
        current_ui.prompt("Press Enter to continue.")
        return

    result = progress.log_progress(entry["name"], amount, expected_kind=kind)
    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")


def toggle_pause(choice: str):
    """Handle pause/unpause from the manager."""
    parts = choice.strip().split()
    if len(parts) < 2:
        current_ui.print_line("Usage: p <#> [days]")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        entry_id = int(parts[1])
    except ValueError:
        current_ui.print_line("ID must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    days = None
    if len(parts) >= 3:
        try:
            days = int(parts[2])
            if days <= 0:
                current_ui.print_line("Days must be positive.")
                current_ui.prompt("Press Enter to continue.")
                return
        except ValueError:
            current_ui.print_line("Days must be a number.")
            current_ui.prompt("Press Enter to continue.")
            return

    result = entries.toggle_pause(entry_id, days)
    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")


def set_daily_total(choice: str, kind: str | None = None):
    """Handle daily_total from manager: dt <#> <total>."""
    parts = choice.strip().split()
    if len(parts) < 3:
        current_ui.print_line("Usage: dt <#> <total>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        entry_id = int(parts[1])
    except ValueError:
        current_ui.print_line("ID must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        total = int(parts[2])
    except ValueError:
        current_ui.print_line("Total must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries.get_entry_by_id(entry_id)
    if not entry:
        current_ui.print_line(f"Entry {entry_id} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    if kind and entry["kind"] != kind:
        current_ui.print_line(f"'{entry['name']}' is a {entry['kind']}, not a {kind}.")
        current_ui.prompt("Press Enter to continue.")
        return

    result = commands.handle_daily_total(f"{entry['name']} {total}", kind)
    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")


def set_counter_total(choice: str, kind: str | None = None):
    """Handle counter_total from manager: ct <#> <value>."""
    parts = choice.strip().split()
    if len(parts) < 3:
        current_ui.print_line("Usage: ct <#> <value>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        entry_id = int(parts[1])
    except ValueError:
        current_ui.print_line("ID must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        value = int(parts[2])
    except ValueError:
        current_ui.print_line("Value must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries.get_entry_by_id(entry_id)
    if not entry:
        current_ui.print_line(f"Entry {entry_id} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    if kind and entry["kind"] != kind:
        current_ui.print_line(f"'{entry['name']}' is a {entry['kind']}, not a {kind}.")
        current_ui.prompt("Press Enter to continue.")
        return

    result = commands.handle_counter_total(f"{entry['name']} {value}", kind)
    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")


def reset_counter(choice: str, kind: str | None = None):
    """Handle counter_reset from manager: cr <#>."""
    parts = choice.strip().split()
    if len(parts) < 2:
        current_ui.print_line("Usage: cr <#>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        entry_id = int(parts[1])
    except ValueError:
        current_ui.print_line("ID must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries.get_entry_by_id(entry_id)
    if not entry:
        current_ui.print_line(f"Entry {entry_id} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    if kind and entry["kind"] != kind:
        current_ui.print_line(f"'{entry['name']}' is a {entry['kind']}, not a {kind}.")
        current_ui.prompt("Press Enter to continue.")
        return

    result = commands.handle_counter_reset(entry["name"], kind)
    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")
