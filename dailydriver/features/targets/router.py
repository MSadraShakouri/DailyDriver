"""Top-level target command routing."""

from . import commands


def dispatch(command: str, kind: str | None = None):
    """Route a ``nazr``, ``habit``, or ``targets`` command."""
    parts = command.strip().split()
    if len(parts) == 1:
        # Keep terminal UI imports out of feature package initialization.
        from .manager import show_manager

        show_manager(kind=kind)
        return None

    subcommand = parts[1].lower()
    args = " ".join(parts[2:])
    handlers = {
        "log": commands.handle_log_command,
        "daily_total": commands.handle_daily_total,
        "counter_total": commands.handle_counter_total,
        "counter_reset": commands.handle_counter_reset,
    }
    handler = handlers.get(subcommand)
    if handler is None:
        return f"Unknown sub-command: {subcommand}\nUsage: nazr log <name> <amount>"
    return handler(args, kind)
