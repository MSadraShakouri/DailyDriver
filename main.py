#!/usr/bin/env python3
import os
from database import init_db
from database import cleanup_pending_keywords
from header_data import build_header_data
from display import print_header
from prayer import log_prayer, log_rq, log_mp
from sleep import log_sleep
from logger import log_free_text, save_pending_start, discard_pending_start, get_pending_start, clear_pending_start
from view import view_entries
from birthday import add_birthday
from hygiene import manage_hygiene
from intention import add_intention
from stats import show_stats
from today import show_today
from flags_manager import manage_flags
from help import show_help

def clear():
    os.system('clear')

def log_event_end(cmd):
    """End the running event and log a free‑text entry."""
    from logger import get_pending_start, clear_pending_start, log_free_text
    started_at = get_pending_start()
    if started_at is None:
        print("No running event to end.")
        return

    # extract description: everything after 'ee' (and optional space)
    # cmd is the whole line. We can split off the first word.
    parts = cmd.strip().split(maxsplit=1)
    text = parts[1] if len(parts) > 1 else ""

    # log the entry, using the saved start time
    result = log_free_text(text, started_at=started_at)
    if result is not None:
        clear_pending_start()
        clear()
        data = build_header_data()
        print_header(data)
        print(result)
    # return None so the REPL doesn't double-print
    return None

def repl():
    init_db()
    cleanup_pending_keywords()   # <-- add this line
    multi_buf = []
    collecting = False

    # Command dispatch map: single‑letter or word to handler function
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
        'ee': log_event_end,   # we'll define this helper
        # free‑text logging is handled in the else case
}

    while True:
        clear()
        data = build_header_data()
        print_header(data)

        if collecting:
            for line in multi_buf:
                print(f"... {line}")
            line = input("... ").strip()
        else:
            line = input("> ").strip()

        if line == '':
            continue

        # Multi‑line sentinel
        if line == '---':
            if collecting:
                full_text = '\n'.join(multi_buf)
                log_free_text(full_text)
                multi_buf = []
                collecting = False
                input("Press Enter to continue.")
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
                result = handler(line) if first in ('p','s','bd','t','ee') else handler(parts)
                if result:
                    clear()
                    data = build_header_data()
                    print_header(data)
                    print(result)
            except KeyboardInterrupt:
                print("\nCancelled.")
                result = None
            input("Press Enter to continue.")
        else:
            # Fall back to free‑text logging
            try:
                result = log_free_text(line)
                if result:
                    clear()
                    data = build_header_data()
                    print_header(data)
                    print(result)
            except KeyboardInterrupt:
                print("\nCancelled.")
                result = None
                input("Press Enter to continue.")

if __name__ == "__main__":
    repl()
