"""Persistent Hijri manual corrections.

The legacy global offset remains supported for compatibility.  New command
choices are stored per Hijri month so a correction for one observed month does
not leak into every later month.
"""

from __future__ import annotations

import json
from pathlib import Path

import jdatetime

OFFSET_FILE = Path(__file__).resolve().parents[3] / "data" / "hijri_offset.txt"
OVERRIDES_FILE = Path(__file__).resolve().parents[3] / "data" / "hijri_overrides.json"


def get_hijri_offset() -> int:
    """Read the legacy global Hijri offset; malformed data means zero."""
    try:
        with open(OFFSET_FILE, encoding="utf-8") as file:
            return int(file.readline().strip())
    except (FileNotFoundError, ValueError):
        return 0


def set_hijri_offset(offset: int) -> None:
    """Persist the legacy global offset together with its selection date.

    This is retained for compatibility with existing data and callers.  The
    interactive command uses :func:`set_hijri_month_offset` instead.
    """
    today = jdatetime.date.today().strftime("%Y-%m-%d")
    with open(OFFSET_FILE, "w", encoding="utf-8") as file:
        file.write(f"{offset}\n{today}\n")
    _invalidate_catalog()


def _month_key(year: int, month: int) -> str:
    return f"{year:04}-{month:02}"


def _load_overrides() -> dict:
    try:
        with open(OVERRIDES_FILE, encoding="utf-8") as file:
            payload = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    overrides = payload.get("overrides", {})
    return overrides if isinstance(overrides, dict) else {}


def _save_overrides(overrides: dict) -> None:
    payload = {"schema_version": 1, "overrides": overrides}
    with open(OVERRIDES_FILE, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
        file.write("\n")


def get_hijri_month_override(year: int, month: int) -> int | None:
    """Return an explicit correction for a Hijri month, if one exists."""
    raw = _load_overrides().get(_month_key(year, month))
    if isinstance(raw, dict):
        raw = raw.get("offset")
    try:
        value = int(raw) if raw is not None else None
    except (TypeError, ValueError):
        return None
    return value if value in range(-2, 3) else None


def get_hijri_month_offset(year: int, month: int) -> int:
    """Return a month-specific correction, falling back to legacy global data."""
    override = get_hijri_month_override(year, month)
    return get_hijri_offset() if override is None else override


def set_hijri_month_offset(year: int, month: int, offset: int) -> None:
    """Persist *offset* for only the selected Hijri month.

    A zero correction normally needs no entry: an absent override already
    means zero when the legacy global correction is zero.  It is stored
    explicitly only when it must mask a nonzero legacy global correction.
    """
    if offset not in range(-2, 3):
        raise ValueError("Hijri offset must be between -2 and +2")
    key = _month_key(year, month)
    overrides = _load_overrides()
    if offset == 0 and get_hijri_offset() == 0:
        if key in overrides:
            del overrides[key]
            _save_overrides(overrides)
        _invalidate_catalog()
        return

    overrides[key] = {
        "offset": offset,
        "set_date": jdatetime.date.today().strftime("%Y-%m-%d"),
    }
    _save_overrides(overrides)
    _invalidate_catalog()


def _invalidate_catalog() -> None:
    # Avoid an import cycle: invalidate an already imported catalog lazily.
    from . import catalog

    catalog.invalidate_cache()
