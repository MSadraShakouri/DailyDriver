"""Targets feature – tracking nazr (finite) and habit (indefinite)."""

from . import _logic, _migrations

NAME = "targets"
VERSION = "1.0.0"


def migrations():
    return _migrations.migrations()


def _targets_dispatcher(cmd: str, kind: str | None = None):
    """
    Dispatcher for targets commands.
    
    kind: 'nazr' or 'habit' to filter entries by kind.
          None means all entries.
    """
    parts = cmd.strip().split()
    
    # Bare command: open manager (Step 3)
    if len(parts) == 1:
        return "Manager not implemented yet (Step 3)"
    
    # Parse sub-command
    sub = parts[1].lower()
    
    if sub == "log":
        return _logic.handle_log_command(cmd, kind)
    else:
        return f"Unknown sub-command: {sub}\nUsage: nazr log <name> <amount>"


def register_commands(dispatch):
    """Register commands with the dispatcher."""
    # nazr → shows only nazr entries
    dispatch["nazr"] = lambda cmd: _targets_dispatcher(cmd, kind="nazr")
    
    # habit → shows only habit entries
    dispatch["habit"] = lambda cmd: _targets_dispatcher(cmd, kind="habit")
    
    # targets → shows all entries
    dispatch["targets"] = lambda cmd: _targets_dispatcher(cmd, kind=None)
