# dailydriver/features/qada/__init__.py
"""Qada feature – prayer backlog and fasting."""

from . import _header, _logic, _manager, _migrations

NAME = "qada"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["qada"] = _logic.qada_command


def header_sections(conn, today, target_date, is_today):
    if not is_today:
        return []
    from datetime import datetime

    now = datetime.now()
    prayer_lines = _header.get_prayer_nudges(conn, target_date, now)
    fasting_lines = _header.get_fasting_nudges(conn, target_date, now)
    lines = prayer_lines + fasting_lines
    return [(33, line) for line in lines]


def migrations():
    return _migrations.migrations()
