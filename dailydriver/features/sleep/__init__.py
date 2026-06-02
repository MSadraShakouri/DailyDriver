# dailydriver/features/sleep/__init__.py
"""Sleep & nap feature – logging and header display."""

from . import _header, _logic

NAME = "sleep"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["s"] = _logic.log_sleep
    dispatch["nap"] = _logic.log_nap


def register_aliases(dispatch):
    dispatch["sleep"] = _logic.log_sleep


def header_sections(conn, today, target_date, is_today):
    from dailydriver.display.display_utils import spread_line

    sleep_str = _header.get_sleep_str(conn, today)
    nap_str = _header.get_nap_str(conn, today)
    if nap_str:
        combined = spread_line([sleep_str, nap_str])
        return [(10, combined)]
    return [(10, sleep_str)]
