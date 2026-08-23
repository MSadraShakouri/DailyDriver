"""Long-running events and activity chaining feature adapter."""

from . import commands, header, state

NAME = "events"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["se"] = lambda _: state.save_pending_start()
    dispatch["ce"] = lambda _: state.discard_pending_start()
    dispatch["ee"] = commands.log_event_end
    dispatch["ln"] = commands.log_chain_now
    dispatch["sge"] = commands.start_great_event_cmd
    dispatch["ege"] = commands.end_great_event_cmd
    dispatch["cge"] = commands.cancel_great_event_cmd
    dispatch["u"] = lambda _: state.update_last_action()
    dispatch["update"] = lambda _: state.update_last_action()


def header_sections(conn, today, target_date, is_today):
    if not is_today:
        return []
    lines = []
    great_event = header.get_great_event_str(is_today)
    if great_event:
        lines.append((5, great_event))
    running_event = header.get_running_event_str(is_today)
    if running_event:
        lines.append((6, running_event))
    return lines
