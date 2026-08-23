"""Core activity state such as the last action timestamp."""

from __future__ import annotations

import time
from datetime import datetime

from .meta import get_meta_value, set_meta_value

_LAST_ACTION_KEY = "last_action"


def get_last_action_time() -> int | None:
    """Return the Unix timestamp of the last successful write, or ``None``."""
    value = get_meta_value(_LAST_ACTION_KEY)
    return int(value) if value else None


def touch_last_action(ts: int | None = None, conn=None) -> int:
    """Persist *ts* as the most recent successful write and return it."""
    timestamp = int(time.time()) if ts is None else int(ts)
    set_meta_value(_LAST_ACTION_KEY, str(timestamp), conn=conn)
    return timestamp


def update_last_action() -> str:
    """Update last_action to now and return a confirmation string."""
    ts = touch_last_action()
    return f"Last action updated to {datetime.fromtimestamp(ts).strftime('%H:%M')}"
