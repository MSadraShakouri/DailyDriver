#!/usr/bin/env python3
"""DailyDriver entry point: REPL, single command, Termux dialog, or --complete / --complete-unfiltered."""

import sys


def _run_shell_completion(args: list[str], filtered: bool = True) -> None:
    """Print candidates for a partial line (shell Tab hook; must stay fast).

    With ``filtered=False`` (``--complete-unfiltered``) every candidate valid at
    the cursor is printed, without narrowing by the word being typed. Shells
    whose completion plugin does its own matching (fzf-tab) ask for this.

    Only the stdlib-only completion engine is imported here — the heavy
    application imports below run afterwards for every other mode.
    """
    try:
        from dailydriver.ui.completion import STATIC_COMMAND_NAMES, suggest_for_text

        for candidate in suggest_for_text(
            " ".join(args), STATIC_COMMAND_NAMES, include_repl_extra=False, filtered=filtered
        ):
            print(candidate)
    except Exception:  # noqa: BLE001, S110 - shell hook must never fail visibly
        pass


def _termux_dialog() -> str | None:
    """Open a Termux text dialog and return the user's input.

    Returns None if the dialog was cancelled or Termux is unavailable.
    Imports are local so `--complete` never pays for them.
    """
    import json
    import shutil
    import subprocess

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
    args = sys.argv[1:]

    # Shell completion hook (see completions/): print candidates for the
    # partial command line, one per line. Runs before everything else —
    # including migrations and feature imports — so every Tab stays fast.
    if args and args[0] in ("--complete", "--complete-unfiltered"):
        _run_shell_completion(args[1:], filtered=args[0] == "--complete")
        sys.exit(0)

    from dailydriver.cli.commander import repl, run_single_command
    from dailydriver.core.migration import run_migrations

    run_migrations()

    # Check for Termux dialog mode
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
