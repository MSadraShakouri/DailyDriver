# dailydriver/cli/commander.py
import sys
from dailydriver.cli.dispatcher import make_dispatch
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.display.header import build_header_data
from dailydriver.display.header_renderer import print_header
from dailydriver.core.logger import log_free_text

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
                            from dailydriver.cli.commands.events import log_chain_now
                            log_chain_now(f'ln {desc}')
                        else:
                            from dailydriver.cli.commands.events import log_event_end
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
                    result = handler(line) if first in ('p','s','bd','t','ee','ln','sge','ege','export','nap', 'search', 'day', 'today', 'pray', 'sleep', 'qada') else handler(parts)
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
    print_header(data, add_separator=False)

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
            result = handler(line) if first in ('p','s','bd','t','ee','ln','sge','ege','export','nap', 'search', 'day', 'today', 'pray', 'sleep', 'qada') else handler(parts)
            if result:
                clear()
                data = build_header_data()
                print_header(data, add_separator=False)
                current_ui.print_line(result)
        except KeyboardInterrupt:
            current_ui.print_line("\nCancelled.")
    else:
        try:
            result = log_free_text(line)
            if result:
                clear()
                data = build_header_data()
                print_header(data, add_separator=False)
                current_ui.print_line(result)
        except KeyboardInterrupt:
            current_ui.print_line("\nCancelled.")

    current_ui.prompt("Press Enter to exit.")
