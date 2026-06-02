# dailydriver/features/__init__.py
"""
Feature packages – see HOOKS.md for the hook specification.
Each enabled feature is imported below.
"""

from . import birthdays, calendar, events, hygiene, intentions, sleep, weather

ENABLED = [events, sleep, weather, hygiene, birthdays, calendar, intentions]
