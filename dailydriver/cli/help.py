# dailydriver/cli/help.py
"""Help rendering built from the single-source-of-truth help registry."""

from dailydriver.cli.help_registry import build_summary, command_help
from dailydriver.ui.terminal_ui import current_ui


def show_help(command_names: list[str] | None = None) -> None:
    """Print the grouped command summary (the ``?`` / ``h`` view)."""
    for line in build_summary(command_names):
        current_ui.print_line(line)


def show_command_help(name: str) -> None:
    """Print the detailed help block for a single command."""
    for line in command_help(name):
        current_ui.print_line(line)
