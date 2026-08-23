"""Void entry command."""

import time

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.ui.terminal_ui import current_ui


def log_void(cmd: str) -> str | None:
    """Log a void entry. No time parsing, categories, keywords, or confirmation."""
    parts = cmd.strip().split(maxsplit=1)
    if len(parts) < 2:
        current_ui.print_line("Void entry requires text. Usage: v <text>")
        return None

    description = parts[1].strip()
    if not description:
        current_ui.print_line("Void entry requires text. Usage: v <text>")
        return None

    now_ts = int(time.time())

    # Use auto=False to avoid updating last_action
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO void_entries (created_at, description) VALUES (?, ?)",
            (now_ts, description),
        )
        conn.commit()

    time_str = jdatetime.datetime.fromtimestamp(now_ts).strftime("%H:%M")
    return f"Void logged at {time_str}"
