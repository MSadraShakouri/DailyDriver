"""Shared unified-timeline collection used by `day` and `export`.

Both commands merge core journal entries with every feature's
``export_items(conn, start, end=None)`` hook into one chronological list.
"""

from __future__ import annotations

import dailydriver.features as features_pkg
from dailydriver.core.journal import get_export_items as get_journal_export_items
from dailydriver.features.registry import export_hook


def collect_timeline_items(conn, start: int, end: int | None = None) -> list[dict]:
    """Return all timeline items in [start, end] sorted chronologically.

    *start* is the inclusive lower timestamp bound (``0`` means all time);
    *end* is an optional inclusive upper bound (``None`` means no upper bound).
    """
    items: list[dict] = list(get_journal_export_items(conn, start, end))
    for feature in features_pkg.ENABLED:
        hook = export_hook(feature)
        if hook is not None:
            items.extend(hook(conn, start, end))
    items.sort(key=lambda item: item.get("sort_key", (item["timestamp"], item["text"])))
    return items
