"""Birthday feature adapter."""

from .commands import add_birthday
from .header import get_birthday_lines
from .manager import manage_birthdays

NAME = "birthdays"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["bd"] = add_birthday
    dispatch["birthdays"] = lambda _: manage_birthdays()


def header_sections(conn, today, target_date, is_today):
    return [(25, line) for line in get_birthday_lines(conn, target_date)]
