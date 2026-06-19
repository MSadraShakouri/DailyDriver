# dailydriver/features/__init__.py
"""
Feature packages – see HOOKS.md for the hook specification.
Each enabled feature is imported below.
"""

from . import weather, hygiene, birthdays, sleep, intentions, calendar, events, prayer

ENABLED = [events, sleep, weather, hygiene, birthdays, calendar, intentions, prayer]
