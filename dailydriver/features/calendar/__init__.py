"""Calendar feature adapter."""

from .commands import hijri_command, show_calendar, show_year
from .sections import build_sections

NAME = "calendar"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["cal"] = show_calendar
    dispatch["year"] = lambda _: show_year()
    dispatch["hijri"] = hijri_command


def header_sections(conn, today, target_date, is_today):
    return build_sections(conn, today, target_date, is_today)
