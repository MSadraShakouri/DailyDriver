# dailydriver/features/__init__.py
"""
Feature packages – see HOOKS.md for the hook specification.
Each enabled feature is imported below.
"""

from . import birthdays, hygiene, intentions, sleep, weather

ENABLED = [sleep, weather, hygiene, birthdays, intentions]
