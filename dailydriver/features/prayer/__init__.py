# dailydriver/features/prayer/__init__.py
"""Prayer feature – logging, qada, pre‑alert / overdue nudges."""
from . import _header
from . import _logic
from . import _migrations

NAME = "prayer"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["p"] = _logic.log_prayer


def register_aliases(dispatch):
    dispatch["pray"] = _logic.log_prayer
    dispatch["qada"] = lambda line: _logic.log_prayer(
        f"p q {line.split(maxsplit=1)[1]}" if len(line.split(maxsplit=1)) > 1 else "p q"
    )


def header_sections(conn, today, target_date, is_today):
    from dailydriver.display.display_utils import spread_line

    parts = _header.get_prayer_parts(conn, today)
    nudges = _header.get_prayer_nudges(conn, target_date, today, is_today)

    result = []
    # prayer spread line as plain string → appears first (no priority needed)
    prayer_line = spread_line(parts, prefix="🕌 ")
    result.append(prayer_line)
    # nudge lines with priority after hygiene
    for n in nudges:
        result.append((32, n))
    return result

def migrations():
    return _migrations.migrations()
