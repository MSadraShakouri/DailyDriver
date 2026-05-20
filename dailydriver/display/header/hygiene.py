# dailydriver/display/header/hygiene.py
"""Hygiene nudge header lines (one per warning)."""

from dailydriver.display.hygiene_nudges import compute_hygiene_nudges


def get_hygiene_lines(conn, target_date, is_today):
    """Return a list of hygiene nudge strings (up to 2)."""
    if is_today:
        nudge_lines = compute_hygiene_nudges(conn, relative_to=target_date)
    else:
        nudge_lines = []
    return nudge_lines[:2]
