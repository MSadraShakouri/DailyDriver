# dailydriver/features/prayer/_logic.py
"""Thin re‑export layer for prayer feature hooks."""
from ._prayer_log import log_prayer
from ._prayer_backlog import log_qada, _update_complete_until
from ._prayer_core import current_slot, PRAYER_SLOTS
from ._prayer_times import get_approximate_times
