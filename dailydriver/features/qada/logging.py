"""Compatibility exports for the former qada logging module.

The implementation lives in :mod:`dailydriver.features.qada.progress`; this
module remains so existing imports keep working.
"""

from .progress import log_fasting, log_prayer_qada, pause_fasting_entry

__all__ = ["log_fasting", "log_prayer_qada", "pause_fasting_entry"]
