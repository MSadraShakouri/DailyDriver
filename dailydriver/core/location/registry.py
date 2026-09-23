"""Static city registry loaded from ``data/cities.json``.

Adding a city is a file edit, not a runtime mutation: each entry carries the
coordinates used by the prayer calculations and the IRIMO weather page URL
used by the weather feature.  Cities without a usable weather page simply
omit ``weather_url`` and the weather line is suppressed for them.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from dailydriver.core.database import PROJECT_ROOT

DEFAULT_CITY_NAME = "Tehran"
REGISTRY_PATH = os.path.join(PROJECT_ROOT, "data", "cities.json")


class RegistryError(RuntimeError):
    """Raised when the city registry is missing or malformed."""


@dataclass(frozen=True)
class City:
    name: str
    lat: float
    lon: float
    tz: float
    weather_url: str | None = None


def load_registry(path: str | None = None) -> dict[str, City]:
    """Load and validate the registry; raise RegistryError when unusable."""
    file_path = path or REGISTRY_PATH
    try:
        with open(file_path, encoding="utf-8") as f:
            raw = json.load(f)
    except FileNotFoundError as exc:
        raise RegistryError(f"City registry not found: {file_path}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RegistryError(f"City registry is not valid JSON: {file_path}") from exc

    if not isinstance(raw, dict) or not raw:
        raise RegistryError("City registry must be a non-empty JSON object")

    cities: dict[str, City] = {}
    for key, entry in raw.items():
        if not isinstance(entry, dict):
            raise RegistryError(f"Malformed city entry: {key!r}")
        try:
            cities[key] = City(
                name=key,
                lat=float(entry["lat"]),
                lon=float(entry["lon"]),
                tz=float(entry["tz"]),
                weather_url=entry.get("weather_url"),
            )
        except (TypeError, KeyError, ValueError) as exc:
            raise RegistryError(f"Malformed city entry: {key!r}") from exc
    return cities


def get_city(name: str, registry: dict[str, City] | None = None) -> City | None:
    """Look up one city, loading the default registry when none is given."""
    cities = registry if registry is not None else load_registry()
    return cities.get(name)
