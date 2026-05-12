from dailydriver.cli.commands.prayer import log_prayer
from dailydriver.cli.commands.sleep import log_sleep, log_nap
from dailydriver.cli.commands.events import (
    log_event_end, log_chain_now,
    start_great_event_cmd, end_great_event_cmd, cancel_great_event_cmd,
)
from dailydriver.cli.commands.journal import log_free_text
from dailydriver.cli.commands.viewing import view_entries, show_day, show_last, show_today
from dailydriver.cli.commands.search import search
from dailydriver.cli.commands.calendar_cmd import show_calendar, show_year
from dailydriver.cli.commands.stats_cmd import show_stats
from dailydriver.cli.commands.birthday_cmd import add_birthday
from dailydriver.cli.commands.hygiene_cmd import manage_hygiene
from dailydriver.cli.commands.intention_cmd import add_intention
from dailydriver.cli.commands.export_cmd import export
from dailydriver.cli.commands.help_cmd import show_help
from dailydriver.ui.terminal_ui import current_ui

def make_dispatch():
    dispatch = {
        'q': lambda _: exit(),
        'p': log_prayer,
        's': log_sleep,
        'view': lambda args: view_entries(args[1] if len(args) > 1 else None),
        '?': lambda _: show_help(),
        'bd': add_birthday,
        'hygiene': lambda _: manage_hygiene(),
        't': add_intention,
        'stats': lambda _: show_stats(),
        'day': show_day,
        'today': show_day,
        'se': lambda _: save_pending_start(),
        'ce': lambda _: discard_pending_start(),
        'ee': log_event_end,
        'ln': log_chain_now,
        'cal': lambda args: show_calendar(args[1:] if len(args) > 1 else []),
        'year': lambda _: show_year(),
        'export': export,
        'nap': log_nap,
        'search': search,
        'last': lambda _: show_last(),
        'sge': start_great_event_cmd,
        'ege': end_great_event_cmd,
        'cge': cancel_great_event_cmd,
        'pray': log_prayer,
        'sleep': log_sleep,
        'h': lambda _: show_help(),
        'qada': lambda line: log_prayer(f'p q {line.split(maxsplit=1)[1]}' if len(line.split(maxsplit=1))>1 else 'p q'),
    }
    return dispatch
