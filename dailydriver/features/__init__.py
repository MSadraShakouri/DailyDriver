"""Enabled DailyDriver feature packages.

Only package-level metadata and hooks are part of the feature contract. See
``HOOKS.md`` and :mod:`dailydriver.features.registry`.
"""

from . import birthdays, calendar, hygiene, intentions, prayer, qada, sleep, targets, void, weather
from .registry import validate_features

ENABLED = validate_features((sleep, weather, hygiene, birthdays, calendar, intentions, prayer, qada, void, targets))
