# dailydriver/cli/commander.py
import sys

from dailydriver.cli.dispatcher import make_dispatch
from dailydriver.cli.help import show_command_help
from dailydriver.core.journal import log_free_text
from dailydriver.display.header import build_header_data
from dailydriver.display.header_renderer import print_header
from dailydriver.ui.terminal_ui import current_ui

HELP_FLAGS = ("-h", "--help")


def clear():
    current_ui.clear()


def _show_result(result):
    """Clear the screen, rebuild the header, and print a result string."""
    clear()
    data = build_header_data()
    print_header(data)
    current_ui.print_line(result)


def _wants_help(parts: list[str]) -> bool:
    """True when a command line carries a -h/--help flag as a distinct token.

    Matched against exact tokens so leading-dash arguments used by logging
    commands (e.g. 'p -15') are never mistaken for a help request.
    """
    return any(token in HELP_FLAGS for token in parts[1:])


def _dispatch_line(line: str, dispatch: dict) -> None:
    """Route a single command line: help flags, then handler, then journal.

    Any command supports -h/--help without each handler implementing it: the
    flag is intercepted here and rendered from the help registry.
    """
    parts = line.split()
    first = parts[0].lower()

    if first in dispatch and _wants_help(parts):
        show_command_help(first)
        return

    handler = dispatch.get(first)
    try:
        if handler:
            result = handler(line)
        else:
            result = log_free_text(line)
        if result:
            _show_result(result)
    except KeyboardInterrupt:
        current_ui.print_line("\nCancelled.")


def _submit_multiline(lines: list[str]) -> None:
    """Submit a collected multiline entry to its real command handler."""
    full_text = "\n".join(lines)
    first_line = lines[0].strip() if lines else ""
    first_parts = first_line.split(maxsplit=1)
    command = first_parts[0].lower() if first_parts else ""

    if command not in ("ln", "ee", "ege"):
        log_free_text(full_text)
        return

    first_description = first_parts[1] if len(first_parts) > 1 else ""
    description_lines = ([first_description] if first_description else []) + lines[1:]
    description = "\n".join(description_lines)

    if command == "ln":
        from dailydriver.cli.commands.events import log_chain_now

        log_chain_now(f"ln {description}")
    elif command == "ege":
        from dailydriver.cli.commands.events import end_great_event_cmd

        end_great_event_cmd(f"ege {description}")
    else:
        from dailydriver.cli.commands.events import log_event_end

        log_event_end(f"ee {description}")


def repl():
    multi_buf = []
    collecting = False

    dispatch = make_dispatch()
    command_names = sorted(dispatch.keys())

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
                line = current_ui.prompt("> ", completions=command_names, history_key="repl").strip()

            if line == "":
                continue

            if line == "---":
                if collecting:
                    _submit_multiline(multi_buf)
                    multi_buf = []
                    collecting = False
                    current_ui.prompt("Press Enter to continue.")
                continue

            if line.lower() == ":m":
                collecting = True
                multi_buf = []
                continue

            if collecting:
                multi_buf.append(line)
                continue

            _dispatch_line(line, dispatch)

            current_ui.prompt("Press Enter to continue.")
    except KeyboardInterrupt:
        current_ui.print_line("\nGoodbye.")
        sys.exit(0)


def run_single_command(line):
    current_ui.clear()
    data = build_header_data()
    print_header(data, add_separator=False)

    if not line:
        current_ui.prompt("Press Enter to exit.")
        return

    current_ui.print_line(f"\n> {line}")

    dispatch = make_dispatch()
    _dispatch_line(line, dispatch)

    current_ui.prompt("Press Enter to exit.")
