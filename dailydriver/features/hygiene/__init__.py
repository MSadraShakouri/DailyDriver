# dailydriver/features/hygiene/__init__.py
"""Hygiene feature – configurable interval nudges."""

from . import _header

NAME = "hygiene"
VERSION = "1.0.0"


def header_sections(conn, today, target_date, is_today):
    lines = _header.get_hygiene_lines(conn, target_date, is_today)
    return [(30, line) for line in lines]  # priority 30 – after weather
