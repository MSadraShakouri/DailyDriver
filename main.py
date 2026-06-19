#!/usr/bin/env python3
import json
import shutil
import subprocess
import sys

from dailydriver.cli.commander import repl, run_single_command
from dailydriver.core.migration import run_migrations


def _termux_dialog() -> str | None:
    """Open a Termux text dialog and return the user's input.
    Returns None if the dialog was cancelled or Termux is unavailable."""
    dialog_path = shutil.which("termux-dialog")
    if not dialog_path:
        print("Termux dialog is only available on Termux.")
        return None

    result = subprocess.run(
        [dialog_path, "text", "-t", "DailyDriver", "-m"],
        capture_output=True,
        text=True,
    )
    try:
        data = json.loads(result.stdout)
        if data.get("code") == -1 and data.get("text"):
            return data.get("text", "").strip()
    except json.JSONDecodeError:
        pass
    return None


if __name__ == "__main__":
    run_migrations()

    # Check for Termux dialog mode
    args = sys.argv[1:]
    if args and args[0] in ("-md", "--termux-dialog"):
        text = _termux_dialog()
        if text:
            run_single_command(text)
        sys.exit(0)

    # Existing behavior: single command or REPL
    if len(sys.argv) > 1:
        run_single_command(" ".join(sys.argv[1:]))
    else:
        repl()
