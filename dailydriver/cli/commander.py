# dailydriver/cli/commander.py
import sys
from datetime import datetime
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.display.header import build_header_data
from dailydriver.display.display_utils import print_header
from dailydriver.domains.prayer_log import log_prayer
from dailydriver.domains.prayer_backlog import log_rq, log_mp
from dailydriver.domains.sleep import log_sleep
from dailydriver.core.logger import (log_free_text, save_pending_start, discard_pending_start,
                                     get_pending_start, clear_pending_start,
                                     start_great_event, get_active_great_event, clear_great_event)
from dailydriver.cli.entry_viewer import view_entries
from dailydriver.domains.birthday import add_birthday
from dailydriver.domains.hygiene import manage_hygiene
from dailydriver.domains.intention import add_intention
from dailydriver.display.stats import show_stats
from dailydriver.display.today import show_today
from dailydriver.cli.help import show_help

def make_dispatch():
    dispatch = {
        'q': lambda _: exit(),
        'p': log_prayer,
        'rq': lambda _: log_rq(),
        'mp': lambda _: log_mp(),
        's': log_sleep,
        'view': lambda args: view_entries(args[1] if len(args) > 1 else None),
        '?': lambda _: show_help(),
        'bd': add_birthday,
        'hygiene': lambda _: manage_hygiene(),
        't': add_intention,
        'stats': lambda _: show_stats(),
        'today': lambda _: show_today(),
        'se': lambda _: save_pending_start(),
        'ce': lambda _: discard_pending_start(),
        'ee': log_event_end,
        'ln': log_chain_now,
    }
    dispatch['sge'] = start_great_event_cmd
    dispatch['ege'] = end_great_event_cmd
    dispatch['cge'] = cancel_great_event_cmd
    return dispatch

def log_event_end(cmd):
    started_at = get_pending_start()
    if started_at is None:
        current_ui.print_line("No running event to end.")
        return

    parts = cmd.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""

    result = log_free_text(text, started_at=started_at)
    if result is not None:
        clear_pending_start()
        current_ui.clear()
        data = build_header_data()
        print_header(data)
        current_ui.print_line(result)
    return None

def log_chain_now(line):
    from dailydriver.core.logger import get_last_action_time
    last_ts = get_last_action_time()
    if last_ts is None:
        current_ui.print_line("No previous action to chain from.")
        return None

    parts = line.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""
    return log_free_text(text, started_at=last_ts)

def start_great_event_cmd(line):
    if get_active_great_event() is not None:
        current_ui.print_line("A great event is already active. Cancel it first (cge).")
        return None

    parts = line.strip().split(maxsplit=1)
    if len(parts) > 1:
        cat_str = parts[1].strip()
        cats = cat_str.split() if cat_str else []
    else:
        cat_input = current_ui.prompt("Great event categories (space‑separated): ").strip()
        cats = cat_input.split() if cat_input else []

    if not cats:
        current_ui.print_line("No categories entered. Great event not started.")
        return None

    cats = [c.lower() for c in cats]
    try:
        ts = start_great_event(cats)
    except RuntimeError as e:
        current_ui.print_line(str(e))
        return None

    time_str = datetime.fromtimestamp(ts).strftime('%H:%M')
    return f"Great event started at {time_str} with: {', '.join(cats)}"

def end_great_event_cmd(line):
    ge = get_active_great_event()
    if ge is None:
        current_ui.print_line("No great event is active.")
        return None
    start_ts, _ = ge

    parts = line.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""

    result = log_free_text(text, started_at=start_ts)
    clear_great_event()
    return result

def cancel_great_event_cmd(line):
    ge = get_active_great_event()
    if ge is None:
        current_ui.print_line("No great event active.")
        return None
    clear_great_event()
    return "Great event cancelled."

def clear():
    current_ui.clear()

def repl():
    multi_buf = []
    collecting = False

    dispatch = make_dispatch()

    try:
        while True:
            current_ui.clear()
            data = build_header_data()
            current_ui.show_header(data)

            if collecting:
                for line in multi_buf:
                    current_ui.print_line(f"... {line}")
                line = current_ui.prompt("... ").strip()
            else:
                line = current_ui.prompt("> ").strip()

            if line == '':
                continue

            if line == '---':
                if collecting:
                    full_text = '\n'.join(multi_buf)
                    first_line = multi_buf[0].strip() if multi_buf else ''
                    first_parts = first_line.split(maxsplit=1)
                    cmd_check = first_parts[0].lower() if first_parts else ''
                    if cmd_check in ('ln', 'ee') and len(first_parts) > 0:
                        rest_first = first_parts[1] if len(first_parts) > 1 else ''
                        if rest_first:
                            new_lines = [rest_first] + multi_buf[1:]
                        else:
                            new_lines = multi_buf[1:]
                        desc = '\n'.join(new_lines) if new_lines else ''
                        if cmd_check == 'ln':
                            log_chain_now(f'ln {desc}')
                        else:
                            log_event_end(f'ee {desc}')
                    else:
                        log_free_text(full_text)
                    multi_buf = []
                    collecting = False
                    current_ui.prompt("Press Enter to continue.")
                continue

            if line.lower() == ':m':
                collecting = True
                multi_buf = []
                continue

            if collecting:
                multi_buf.append(line)
                continue

            parts = line.split()
            first = parts[0].lower()

            handler = dispatch.get(first)
            if handler:
                try:
                    result = handler(line) if first in ('p','s','bd','t','ee','ln','sge','ege') else handler(parts)
                    if result:
                        clear()
                        data = build_header_data()
                        print_header(data)
                        current_ui.print_line(result)
                except KeyboardInterrupt:
                    current_ui.print_line("\nCancelled.")
            else:
                try:
                    result = log_free_text(line)
                    if result:
                        clear()
                        data = build_header_data()
                        print_header(data)
                        current_ui.print_line(result)
                except KeyboardInterrupt:
                    current_ui.print_line("\nCancelled.")

            current_ui.prompt("Press Enter to continue.")
    except KeyboardInterrupt:
        current_ui.print_line("\nGoodbye.")
        sys.exit(0)

def run_single_command(line):
    current_ui.clear()
    data = build_header_data()
    current_ui.show_header(data)

    if not line:
        current_ui.prompt("Press Enter to exit.")
        return

    current_ui.print_line(f"\n> {line}")

    dispatch = make_dispatch()
    parts = line.split()
    first = parts[0].lower()

    handler = dispatch.get(first)
    if handler:
        try:
            result = handler(line) if first in ('p','s','bd','t','ee','ln','sge','ege') else handler(parts)
            if result:
                clear()
                data = build_header_data()
                print_header(data)
                current_ui.print_line(result)
        except KeyboardInterrupt:
            current_ui.print_line("\nCancelled.")
    else:
        try:
            result = log_free_text(line)
            if result:
                clear()
                data = build_header_data()
                print_header(data)
                current_ui.print_line(result)
        except KeyboardInterrupt:
            current_ui.print_line("\nCancelled.")

    current_ui.prompt("Press Enter to exit.")
