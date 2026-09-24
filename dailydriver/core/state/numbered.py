"""Persistence for the nine numbered, category-injecting journal states."""

from __future__ import annotations

import re
import time
from datetime import datetime

from dailydriver.core.database import get_connection_cm

from .activity import touch_last_action
from .events import get_active_great_event

STATE_IDS = tuple(range(1, 10))
_KEY_RE = re.compile(r"^numbered_state_([1-9])_(start|categories)$")


def _validate_state_id(state_id: int) -> int:
    try:
        value = int(state_id)
    except (TypeError, ValueError) as error:
        raise ValueError("State number must be from 1 to 9.") from error
    if value not in STATE_IDS:
        raise ValueError("State number must be from 1 to 9.")
    return value


def _start_key(state_id: int) -> str:
    return f"numbered_state_{state_id}_start"


def _categories_key(state_id: int) -> str:
    return f"numbered_state_{state_id}_categories"


def _normalise_categories(categories: list[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in categories:
        path = raw.strip().lower()
        if not path:
            continue
        if any(character.isspace() for character in path):
            raise ValueError("Category paths cannot contain whitespace; separate categories with spaces.")
        if path not in seen:
            result.append(path)
            seen.add(path)
    if not result:
        raise ValueError("At least one category is required for a state.")
    return result


def start_numbered_state(state_id: int, categories: list[str], update_last: bool = False) -> int:
    """Start a free numbered state and ensure all of its categories exist.

    Category rows, state metadata, and the optional last-action update are
    written together. Existing categories are looked up before insertion so a
    duplicate path does not consume an AUTOINCREMENT ID.
    """
    state_id = _validate_state_id(state_id)
    paths = _normalise_categories(categories)

    with get_connection_cm(auto=False) as conn:
        if conn.execute("SELECT 1 FROM meta WHERE key = ?", (_start_key(state_id),)).fetchone():
            raise RuntimeError(f"State {state_id} is already active.")

        for path in paths:
            exists = conn.execute("SELECT 1 FROM categories WHERE path = ?", (path,)).fetchone()
            if not exists:
                conn.execute("INSERT INTO categories (path) VALUES (?)", (path,))

        timestamp = int(time.time())
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (_start_key(state_id), str(timestamp)),
        )
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)",
            (_categories_key(state_id), " ".join(paths)),
        )
        if update_last:
            touch_last_action(timestamp, conn=conn)
        else:
            conn.commit()
    return timestamp


def get_active_numbered_states() -> list[dict]:
    """Return active states in slot order with their start time and categories."""
    with get_connection_cm(auto=False) as conn:
        rows = conn.execute("SELECT key, value FROM meta WHERE key LIKE 'numbered_state_%'").fetchall()

    values: dict[int, dict[str, str]] = {}
    for row in rows:
        match = _KEY_RE.fullmatch(row["key"])
        if match:
            state_id = int(match.group(1))
            values.setdefault(state_id, {})[match.group(2)] = row["value"] or ""

    active: list[dict] = []
    for state_id in sorted(values):
        state = values[state_id]
        try:
            started_at = int(state.get("start", ""))
        except (TypeError, ValueError):
            continue
        categories = state.get("categories", "").split()
        active.append({"id": state_id, "started_at": started_at, "categories": categories})
    return active


def clear_numbered_states(state_ids: list[int]) -> None:
    """Close the selected active slots without changing ``last_action``."""
    ids = [_validate_state_id(state_id) for state_id in state_ids]
    if not ids:
        return
    keys = [key for state_id in ids for key in (_start_key(state_id), _categories_key(state_id))]
    placeholders = ", ".join("?" for _ in keys)
    with get_connection_cm(auto=False) as conn:
        conn.execute(f"DELETE FROM meta WHERE key IN ({placeholders})", keys)
        conn.commit()


def get_active_numbered_categories() -> list[str]:
    """Return deduplicated injected category paths from active numbered states."""
    result: list[str] = []
    seen: set[str] = set()
    for state in get_active_numbered_states():
        for path in state["categories"]:
            if path not in seen:
                result.append(path)
                seen.add(path)
    return result


def get_active_injected_categories() -> list[str]:
    """Return the deduplicated categories injected by all active event systems."""
    result: list[str] = []
    seen: set[str] = set()

    active_great_event = get_active_great_event()
    categories = list(active_great_event[1]) if active_great_event else []
    categories.extend(get_active_numbered_categories())
    for path in categories:
        if path not in seen:
            result.append(path)
            seen.add(path)
    return result


def format_numbered_states() -> str:
    """Format active state slots for the daily header."""
    pieces = []
    for state in get_active_numbered_states():
        started = datetime.fromtimestamp(state["started_at"]).strftime("%H:%M")
        categories = ", ".join(state["categories"])
        pieces.append(f"{state['id']} [{categories}] since {started}")
    return "⏱ States: " + " | ".join(pieces) if pieces else ""
