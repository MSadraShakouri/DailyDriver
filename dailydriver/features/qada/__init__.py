# dailydriver/features/qada/__init__.py
"""Qada feature – prayer backlog and fasting."""

NAME = "qada"
VERSION = "1.0.0"


from . import _header, _logic


def register_commands(dispatch):
    dispatch["qada"] = _logic.qada_command


def header_sections(conn, today, target_date, is_today):
    if not is_today:
        return []
    from datetime import datetime

    lines = _header.get_prayer_nudges(conn, target_date, datetime.now())
    return [(33, line) for line in lines]  # priority 33 – right after prayer nudges (32)


def migrations():
    return []
