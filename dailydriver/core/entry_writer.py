"""Backward-compatible journal persistence helpers."""

from dailydriver.core.journal.writer import inject_great_categories, save_entry

_save_entry = save_entry

__all__ = ["_save_entry", "inject_great_categories", "save_entry"]
