"""Compatibility imports for the historical CLI viewing module path."""

from dailydriver.cli.day_view import show_day
from dailydriver.cli.entry_viewer import view_entries
from dailydriver.cli.last_view import show_last

__all__ = ["view_entries", "show_day", "show_last"]
