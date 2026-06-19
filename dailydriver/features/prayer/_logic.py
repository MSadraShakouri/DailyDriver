# dailydriver/features/prayer/_logic.py
"""Thin re‑export layer for prayer feature hooks."""

from ._prayer_backlog import _update_complete_until, log_qada
from ._prayer_core import PRAYER_SLOTS, current_slot
from ._prayer_log import log_prayer
from ._prayer_times import get_approximate_times
