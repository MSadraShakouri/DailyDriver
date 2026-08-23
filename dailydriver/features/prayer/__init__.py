"""Prayer logging and reminder feature adapter."""

from dailydriver.display.display_utils import spread_line

from .commands import log_prayer
from .export import export_items
from .nudges import get_prayer_nudges
from .status import get_prayer_parts

NAME = "prayer"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["p"] = log_prayer
    dispatch["pray"] = log_prayer



def header_sections(conn, today, target_date, is_today):
    sections = [(0, spread_line(get_prayer_parts(conn, today), prefix="🕌 "))]
    sections.extend((32, nudge) for nudge in get_prayer_nudges(conn, target_date, today, is_today))
    return sections
