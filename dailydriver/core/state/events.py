"""Persistent state for chaining, pending events, and great events."""

from __future__ import annotations

import time
from datetime import datetime

from dailydriver.core.database import get_connection_cm

from .meta import delete_meta_keys, get_meta_int, get_meta_value, set_meta_value

_PENDING_START_KEY = "pending_start"
_GREAT_EVENT_START_KEY = "great_event_start"
_GREAT_EVENT_CATEGORIES_KEY = "great_event_categories"


def save_pending_start() -> str:
    ts = int(time.time())
    set_meta_value(_PENDING_START_KEY, str(ts))
    from .activity import touch_last_action

    touch_last_action(ts)
    return f"Start saved: {datetime.fromtimestamp(ts).strftime('%H:%M')}"


def discard_pending_start() -> str:
    ts = get_meta_int(_PENDING_START_KEY)
    if ts is None:
        return "No saved start to discard."
    delete_meta_keys(_PENDING_START_KEY)
    return f"Saved start ({datetime.fromtimestamp(ts).strftime('%H:%M')}) discarded."


def get_pending_start() -> int | None:
    return get_meta_int(_PENDING_START_KEY)


def clear_pending_start() -> None:
    delete_meta_keys(_PENDING_START_KEY)


def start_great_event(categories: list[str]) -> int:
    with get_connection_cm(auto=False) as conn:
        if get_meta_value(_GREAT_EVENT_START_KEY, conn=conn) is not None:
            raise RuntimeError("A great event is already active.")
        # Great-event categories are injected later by the journal writer, so
        # materialise new paths now. Check first: INSERT OR IGNORE on the
        # AUTOINCREMENT categories table consumes IDs on duplicate paths.
        for category in categories:
            exists = conn.execute("SELECT 1 FROM categories WHERE path = ?", (category,)).fetchone()
            if not exists:
                conn.execute("INSERT INTO categories (path) VALUES (?)", (category,))

        ts = int(time.time())
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (_GREAT_EVENT_START_KEY, str(ts)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (_GREAT_EVENT_CATEGORIES_KEY, " ".join(categories)),
        )
        conn.commit()
        from .activity import touch_last_action

        touch_last_action(ts)
        return ts


def get_active_great_event() -> tuple[int, list[str]] | None:
    with get_connection_cm(auto=False) as conn:
        start_ts = get_meta_int(_GREAT_EVENT_START_KEY, conn=conn)
        if start_ts is None:
            return None
        categories_value = get_meta_value(_GREAT_EVENT_CATEGORIES_KEY, "", conn=conn) or ""
        categories = categories_value.split() if categories_value.strip() else []
        return start_ts, categories


def clear_great_event() -> None:
    delete_meta_keys(_GREAT_EVENT_START_KEY, _GREAT_EVENT_CATEGORIES_KEY)
