"""Persistent Hijri moon-sighting offset."""

from pathlib import Path

import jdatetime

OFFSET_FILE = Path(__file__).resolve().parents[3] / "data" / "hijri_offset.txt"


def get_hijri_offset() -> int:
    """Read the current Hijri offset; malformed or absent data means zero."""
    try:
        with open(OFFSET_FILE, encoding="utf-8") as file:
            return int(file.readline().strip())
    except (FileNotFoundError, ValueError):
        return 0


def set_hijri_offset(offset: int) -> None:
    """Persist *offset* together with the date on which it was chosen."""
    today = jdatetime.date.today().strftime("%Y-%m-%d")
    with open(OFFSET_FILE, "w", encoding="utf-8") as file:
        file.write(f"{offset}\n{today}\n")

    # Avoid an import cycle: invalidate an already imported catalog lazily.
    from . import catalog

    catalog.invalidate_cache()
