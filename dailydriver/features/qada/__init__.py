# dailydriver/features/qada/__init__.py
"""Qada feature – prayer backlog and fasting."""

NAME = "qada"
VERSION = "1.0.0"


from . import _logic


def register_commands(dispatch):
    dispatch["qada"] = _logic.qada_command


def header_sections(conn, today, target_date, is_today):
    if not is_today:
        return []
    return []


def migrations():
    return []
