"""Location infrastructure: city registry, schedule rules, state, resolution.

This is core infrastructure, not a feature package: the prayer and weather
features and the ``city`` command all import from here, and nothing here
imports from features (same precedent as events & chaining).  Disabling a
feature can never break it.
"""

from dailydriver.core.location.registry import City, RegistryError, load_registry
from dailydriver.core.location.resolver import CityInfo, resolve_city

__all__ = ["City", "CityInfo", "RegistryError", "load_registry", "resolve_city"]
