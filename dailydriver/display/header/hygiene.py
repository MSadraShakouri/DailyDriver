# dailydriver/display/header/hygiene.py
"""Hygiene nudge header line."""
from dailydriver.display.hygiene_nudges import compute_hygiene_nudges

def get_hygiene_str(conn, target_date, is_today):
    if is_today:
        nudge_lines = compute_hygiene_nudges(conn, relative_to=target_date)
    else:
        nudge_lines = []
    return "   ".join(nudge_lines[:2])
