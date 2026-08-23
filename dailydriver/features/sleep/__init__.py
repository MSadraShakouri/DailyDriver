"""Sleep and nap feature adapter."""

from dailydriver.display.display_utils import spread_line

from .commands import log_nap, log_sleep
from .export import export_items
from .migrations import migrations
from .status import get_nap_str, get_sleep_str

NAME = "sleep"
VERSION = "1.0.0"


def register_commands(dispatch):
    dispatch["s"] = log_sleep
    dispatch["sleep"] = log_sleep
    dispatch["nap"] = log_nap



def header_sections(conn, today, target_date, is_today):
    sleep = get_sleep_str(conn, today)
    nap = get_nap_str(conn, today)
    return [(10, spread_line([sleep, nap]) if nap else sleep)]
