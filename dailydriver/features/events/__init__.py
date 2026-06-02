# dailydriver/features/events/__init__.py
"""Great events, running events, and chaining."""

from . import _header, _logic

NAME = "events"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["se"] = _logic.save_pending_start
    dispatch["ce"] = _logic.discard_pending_start
    dispatch["ee"] = _logic.log_event_end
    dispatch["ln"] = _logic.log_chain_now
    dispatch["sge"] = _logic.start_great_event_cmd
    dispatch["ege"] = _logic.end_great_event_cmd
    dispatch["cge"] = _logic.cancel_great_event_cmd


def header_sections(conn, today, target_date, is_today):
    lines = []
    if is_today:
        ge = _header.get_great_event_str(is_today)
        if ge:
            lines.append((5, ge))
        re = _header.get_running_event_str(is_today)
        if re:
            lines.append((6, re))
    return lines
