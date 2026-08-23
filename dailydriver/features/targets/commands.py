"""Quick target subcommand handlers."""

from dailydriver.ui.terminal_ui import current_ui

from . import clock
from .entries import get_entry_by_name
from .history import get_counter_value, get_daily_total, set_counter_value
from .progress import log_progress


def handle_log_command(args: str, kind: str | None = None) -> str:
    """Handle 'nazr log' or 'habit log' commands.
    kind: 'nazr' or 'habit' to validate the entry kind.
    Returns a confirmation string or an error message.
    """
    parts = args.strip().split()
    if len(parts) < 2:
        return "Usage: log <name> <amount>"
    name, amount_str = parts[0], parts[1]
    try:
        amount = int(amount_str)
    except ValueError:
        return "Amount must be a number."
    if amount <= 0:
        return "Amount must be positive."
    return log_progress(name, amount, expected_kind=kind)


def handle_daily_total(args: str, kind: str | None = None) -> str:
    """
    Usage: nazr daily_total <name> <total>
           habit daily_total <name> <total>
    Logs the difference between total and what's already logged today.
    """
    parts = args.strip().split()
    if len(parts) != 2:
        return "Usage: daily_total <name> <total>"
    name, total_str = parts[0], parts[1]
    try:
        total = int(total_str)
    except ValueError:
        return "Total must be a number."

    entry = get_entry_by_name(name)
    if not entry:
        return f"Entry not found: {name}"
    if kind and entry["kind"] != kind:
        return f"'{name}' is a {entry['kind']}, not a {kind}."

    today = clock.today()
    today_total = get_daily_total(entry["id"], today)
    diff = total - today_total
    if diff == 0:
        return "No change. Nothing logged."
    if diff < 0:
        current_ui.print_line(f"Warning: Total {total} is less than today's logged total ({today_total}).")
        return "Negative amount not logged. Please adjust manually."
    return log_progress(name, diff, kind)


def handle_counter_total(args: str, kind: str | None = None) -> str:
    """
    Usage: nazr counter_total <name> <value>
           habit counter_total <name> <value>
    Logs the difference between value and the stored counter value.
    Updates the stored counter value after logging.
    """
    parts = args.strip().split()
    if len(parts) != 2:
        return "Usage: counter_total <name> <value>"
    name, value_str = parts[0], parts[1]
    try:
        value = int(value_str)
    except ValueError:
        return "Value must be a number."

    entry = get_entry_by_name(name)
    if not entry:
        return f"Entry not found: {name}"
    if kind and entry["kind"] != kind:
        return f"'{name}' is a {entry['kind']}, not a {kind}."

    last = get_counter_value(entry["id"])
    diff = value - last
    if diff == 0:
        return "No change. Nothing logged."
    if diff < 0:
        current_ui.print_line(f"Warning: Counter value {value} is less than previous value ({last}).")
        return "Negative amount not logged. Please adjust manually."

    set_counter_value(entry["id"], value)
    return log_progress(name, diff, kind)


def handle_counter_reset(args: str, kind: str | None = None) -> str:
    """
    Usage: nazr counter_reset <name>
           habit counter_reset <name>
    Resets the stored counter value to 0. Does not log anything.
    """
    parts = args.strip().split()
    if len(parts) != 1:
        return "Usage: counter_reset <name>"
    name = parts[0]

    entry = get_entry_by_name(name)
    if not entry:
        return f"Entry not found: {name}"
    if kind and entry["kind"] != kind:
        return f"'{name}' is a {entry['kind']}, not a {kind}."

    set_counter_value(entry["id"], 0)
    return f"Counter reset to 0 for {name}"
