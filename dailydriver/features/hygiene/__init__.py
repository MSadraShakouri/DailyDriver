"""Hygiene interval feature adapter."""

from .header import get_hygiene_lines

NAME = "hygiene"
VERSION = "1.0.0"


def header_sections(conn, today, target_date, is_today):
    return [(30, line) for line in get_hygiene_lines(conn, target_date, is_today)]
