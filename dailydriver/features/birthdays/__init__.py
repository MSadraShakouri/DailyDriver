# dailydriver/features/birthdays/__init__.py
"""Birthday feature – list, add, toggle reminders, header lines."""

from . import _header, _logic

NAME = "birthdays"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["bd"] = _logic.add_birthday
    dispatch["birthdays"] = lambda _: _logic.manage_birthdays()


def header_sections(conn, today, target_date, is_today):
    lines = _header.get_birthday_lines(conn, target_date)
    return [
        (25, line) for line in lines
    ]  # priority 25 – between weather (20) and hygiene (30)
