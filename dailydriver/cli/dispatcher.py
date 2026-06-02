import sys

import dailydriver.features as features_pkg
from dailydriver.cli.commands.export_cmd import export
from dailydriver.cli.commands.help_cmd import show_help
from dailydriver.cli.commands.hygiene_cmd import manage_hygiene
from dailydriver.cli.commands.prayer import log_prayer
from dailydriver.cli.commands.search import search
from dailydriver.cli.commands.stats_cmd import show_stats
from dailydriver.cli.commands.viewing import show_day, show_last, view_entries
from dailydriver.features.events._logic import discard_pending_start, save_pending_start


def make_dispatch():
    dispatch = {
        "q": lambda _: sys.exit(0),
        "p": log_prayer,
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
        "pray": log_prayer,
        "h": lambda _: show_help(),
        "qada": lambda line: log_prayer(
            f"p q {line.split(maxsplit=1)[1]}" if len(line.split(maxsplit=1)) > 1 else "p q"
        ),
    }

    # Let features register their own commands
    for feature in features_pkg.ENABLED:
        if hasattr(feature, "register_commands"):
            feature.register_commands(dispatch)

        # Let features register their own aliases
        if hasattr(feature, "register_aliases"):
            feature.register_aliases(dispatch)

    return dispatch
