"""Qada prayer and fasting feature adapter."""

from datetime import datetime

from .commands import qada_command
from .export import export_items
from .header import get_fasting_nudges, get_prayer_nudges
from .migrations import migrations

NAME = "qada"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["qada"] = qada_command



def header_sections(conn, today, target_date, is_today):
    if not is_today:
        return []
    now = datetime.now()
    lines = get_prayer_nudges(conn, target_date, now) + get_fasting_nudges(conn, target_date, now)
    return [(33, line) for line in lines]
