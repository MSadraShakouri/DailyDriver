#!/usr/bin/env python3
import os
import sys
from ui import current_ui
from database import init_db, cleanup_pending_keywords
from header_data import build_header_data
from display import print_header
from prayer import log_prayer, log_rq, log_mp
from sleep import log_sleep
from logger import (log_free_text, save_pending_start, discard_pending_start,
                    get_pending_start, clear_pending_start,
                    start_great_event, get_active_great_event, clear_great_event)
from view import view_entries
from birthday import add_birthday
from hygiene import manage_hygiene
from intention import add_intention
from stats import show_stats
from today import show_today
from flags_manager import manage_flags
from help import show_help
from datetime import datetime

# ----------------------------------------------------------------------
#  Dispatch helpers
# ----------------------------------------------------------------------
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
        'flags': lambda _: manage_flags(),
        'se': lambda _: save_pending_start(),
        'ce': lambda _: discard_pending_start(),
        'ee': log_event_end,
        'ln': log_chain_now,
    }
    # Great-event commands
    dispatch['sge'] = start_great_event_cmd
    dispatch['ege'] = end_great_event_cmd
    dispatch['cge'] = cancel_great_event_cmd
    return dispatch

# ----------------------------------------------------------------------
#  Event / chain logging
# ----------------------------------------------------------------------
def log_event_end(cmd):
    """End the running event and log a free‑text entry."""
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
    """ln command: log from last action time until now."""
    from logger import get_last_action_time
    last_ts = get_last_action_time()
    if last_ts is None:
        current_ui.print_line("No previous action to chain from.")
        return None

    parts = line.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""
    return log_free_text(text, started_at=last_ts)

# ----------------------------------------------------------------------
#  Great‑event command handlers
# ----------------------------------------------------------------------
def start_great_event_cmd(line):
    """sge [category1 category2 ...] – Start a great event."""
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
    """ege [description] – End the great event and log like ee."""
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
    """cge – Cancel the great event."""
    ge = get_active_great_event()
    if ge is None:
        current_ui.print_line("No great event active.")
        return None
    clear_great_event()
    return "Great event cancelled."

# ----------------------------------------------------------------------
#  REPL & CLI
# ----------------------------------------------------------------------
def clear():
    current_ui.clear()

def repl():
    init_db()
    cleanup_pending_keywords()
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

            # Multi‑line sentinel
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

            # ---------- normal command processing ----------
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
                    result = None
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
                    result = None

            current_ui.prompt("Press Enter to continue.")
    except KeyboardInterrupt:
        current_ui.print_line("\nGoodbye.")
        sys.exit(0)

def run_single_command(line):
    init_db()
    cleanup_pending_keywords()

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

if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_single_command(' '.join(sys.argv[1:]))
    else:
        repl()
