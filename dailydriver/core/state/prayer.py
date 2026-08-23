"""Prayer-related progress state stored in the meta table."""

from __future__ import annotations

from .meta import get_meta_value, set_meta_value

_COMPLETE_UNTIL_KEY = "prayer_complete_until"


def get_prayer_complete_until(conn=None) -> str | None:
    return get_meta_value(_COMPLETE_UNTIL_KEY, conn=conn)



def set_prayer_complete_until(date_str: str, conn=None) -> None:
    set_meta_value(_COMPLETE_UNTIL_KEY, date_str, conn=conn)
