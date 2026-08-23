"""Travel mode state management."""

from __future__ import annotations

from .meta import delete_meta_keys, get_meta_value, set_meta_value

_TRAVEL_MODE_KEY = "travel_mode"


def is_travel_mode() -> bool:
    """Return ``True`` when travel mode is enabled."""
    return get_meta_value(_TRAVEL_MODE_KEY) == "1"


def set_travel_mode(enabled: bool) -> None:
    """Enable or disable travel mode."""
    if enabled:
        set_meta_value(_TRAVEL_MODE_KEY, "1")
    else:
        delete_meta_keys(_TRAVEL_MODE_KEY)
