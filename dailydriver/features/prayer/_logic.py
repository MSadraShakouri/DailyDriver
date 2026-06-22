# dailydriver/features/prayer/_logic.py
"""Thin re‑export layer for prayer feature hooks."""

from ._prayer_backlog import _update_complete_until, log_qada  # noqa: F401
from ._prayer_core import PRAYER_SLOTS, current_slot  # noqa: F401
from ._prayer_log import log_prayer  # noqa: F401 (re‑exported)
