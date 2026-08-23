import sys

import dailydriver.features as features_pkg
from dailydriver.features.registry import command_hook
from dailydriver.cli.commands.export_cmd import export
from dailydriver.cli.commands.help_cmd import show_help
from dailydriver.cli.commands.hygiene_cmd import manage_hygiene
from dailydriver.cli.commands.search import search
from dailydriver.cli.commands.stats_cmd import show_stats
from dailydriver.cli.commands.viewing import show_day, show_last, view_entries
from dailydriver.features.events.state import discard_pending_start, save_pending_start

from .commands.daystart import daystart_command
from .commands.travel import travel_command


def make_dispatch():
    dispatch = {
        "q": lambda _: sys.exit(0),
        "view": lambda line: view_entries(line.split(maxsplit=1)[1] if len(line.split()) > 1 else None),
        "?": lambda _: show_help(),
        "hygiene": lambda _: manage_hygiene(),
        "stats": lambda _: show_stats(),
        "day": show_day,
        "today": show_day,
        "se": lambda _: save_pending_start(),
        "ce": lambda _: discard_pending_start(),
        "export": export,
        "search": search,
        "recent": lambda _: show_last(),
        "h": lambda _: show_help(),
        "travel": travel_command,
        "daystart": daystart_command,
    }

    # Features expose command registration as an optional package capability.
    for feature in features_pkg.ENABLED:
        register = command_hook(feature)
        if register is not None:
            register(dispatch)

    return dispatch
