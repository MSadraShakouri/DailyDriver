# dailydriver/features/qada/_manager.py
"""Interactive qada manager."""

import textwrap

import jdatetime

from dailydriver.display.display_utils import get_width
from dailydriver.features.qada import _logic
from dailydriver.ui.terminal_ui import current_ui


def show_qada_manager():
    """Main loop for the qada manager."""
    while True:
        current_ui.clear()
        entries = _logic.get_all_entries_with_progress()

        # Render table
        _render_entries(entries)

        # Show commands
        current_ui.print_line("\n(l)og  (p)ause  (e)dit  (q)uit")
        choice = current_ui.prompt("> ").strip().lower()

        if choice == "q":
            break
        elif choice.startswith("l "):
            _log_entry(choice)
        elif choice.startswith("p "):
            _pause_entry(choice)
        elif choice.startswith("e "):
            _edit_entry(choice)
        else:
            current_ui.print_line("Unknown command.")
            current_ui.prompt("Press Enter to continue.")


def _render_entries(entries):
    """Render the qada entries table."""
    tw = get_width()
    # Fixed columns
    idx_width = 2
    name_width = 14  # "Dhuhr/Asr" is 9, "Maghrib/Isha" is 12, "Fasting" is 7
    prog_width = 10
    pct_width = 8
    next_width = 10
    # Total: 2 + 14 + 10 + 8 + 10 = 44, plus spaces = ~48

    # Header
    header = f"{'#':>{idx_width}}  {'Name':<{name_width}}  {'Progress':<{prog_width}}  {'%':<{pct_width}}  {'Next':<{next_width}}"
    current_ui.print_line(header)
    current_ui.print_line("─" * min(tw, len(header)))

    for entry in entries:
        idx = entry["index"]
        name = entry["name"]
        prog = entry["progress_display"]
        pct = entry["percentage"] if entry["percentage"] else ""
        next_date = entry["next_instance"].strftime("%Y-%m-%d") if entry["next_instance"] else "-"

        # Truncate if needed
        if len(name) > name_width:
            name = name[: name_width - 1] + "…"

        line = f"{idx:>{idx_width}}  {name:<{name_width}}  {prog:<{prog_width}}  {pct:<{pct_width}}  {next_date:<{next_width}}"

        # Apply colors
        target = entry["target_total"]
        if target == -1:
            # Not set – yellow
            line = f"\033[33m{line}\033[0m"
        elif entry["is_complete"]:
            # Complete – green
            line = f"\033[32m{line}\033[0m"
        elif entry["is_paused"]:
            # Paused – dimmed
            line = f"\033[2m{line}\033[0m"

        current_ui.print_line(line)


def _log_entry(choice):
    """Log progress for an entry."""
    parts = choice.split()
    if len(parts) < 2:
        current_ui.print_line("Usage: l <#>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        idx = int(parts[1])
    except ValueError:
        current_ui.print_line("Invalid number.")
        current_ui.prompt("Press Enter to continue.")
        return

    entries = _logic.get_all_entries_with_progress()
    if idx < 1 or idx > len(entries):
        current_ui.print_line(f"Entry #{idx} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries[idx - 1]
    target = entry["target_total"]

    if target <= 0:
        current_ui.print_line("Nothing to log (target not set or complete).")
        current_ui.prompt("Press Enter to continue.")
        return

    amount_str = current_ui.prompt(f"Amount to log (Enter=1): ").strip()
    try:
        amount = int(amount_str) if amount_str else 1
    except ValueError:
        current_ui.print_line("Invalid number.")
        current_ui.prompt("Press Enter to continue.")
        return

    if amount <= 0:
        current_ui.print_line("Amount must be positive.")
        current_ui.prompt("Press Enter to continue.")
        return

    if entry["kind"] == "prayer":
        result = _logic.log_prayer_qada(entry["id"], amount)
    else:  # fasting
        result = _logic.log_fasting(entry["id"])

    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")


def _pause_entry(choice):
    """Pause or unpause an entry."""
    parts = choice.split()
    if len(parts) < 2:
        current_ui.print_line("Usage: p <#>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        idx = int(parts[1])
    except ValueError:
        current_ui.print_line("Invalid number.")
        current_ui.prompt("Press Enter to continue.")
        return

    entries = _logic.get_all_entries_with_progress()
    if idx < 1 or idx > len(entries):
        current_ui.print_line(f"Entry #{idx} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries[idx - 1]
    entry_id = entry["id"]

    if entry["target_total"] == -1:
        current_ui.print_line("Entry not set. Use 'e' first.")
        current_ui.prompt("Press Enter to continue.")
        return

    if entry["is_paused"]:
        confirm = current_ui.prompt("Unpause? (y/n): ").strip().lower()
        if confirm == "y":
            _logic.edit_entry(entry_id, paused_until=None)
            current_ui.print_line("Entry unpaused.")
        else:
            current_ui.print_line("Cancelled.")
        current_ui.prompt("Press Enter to continue.")
        return

    days_str = current_ui.prompt("Pause for N days (Enter=1): ").strip()
    try:
        days = int(days_str) if days_str else 1
    except ValueError:
        current_ui.print_line("Invalid number.")
        current_ui.prompt("Press Enter to continue.")
        return

    if days <= 0:
        current_ui.print_line("Days must be positive.")
        current_ui.prompt("Press Enter to continue.")
        return

    today = jdatetime.date.today()
    pause_until = today + jdatetime.timedelta(days=days)
    _logic.edit_entry(entry_id, paused_until=pause_until.strftime("%Y-%m-%d"))

    current_ui.print_line(f"Paused for {days} days (until {pause_until.strftime('%Y-%m-%d')}).")
    current_ui.prompt("Press Enter to continue.")


def _edit_entry(choice):
    """Edit an entry (creates if missing)."""
    parts = choice.split()
    if len(parts) < 2:
        current_ui.print_line("Usage: e <#>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        idx = int(parts[1])
    except ValueError:
        current_ui.print_line("Invalid number.")
        current_ui.prompt("Press Enter to continue.")
        return

    entries = _logic.get_all_entries_with_progress()
    if idx < 1 or idx > len(entries):
        current_ui.print_line(f"Entry #{idx} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries[idx - 1]
    entry_id = entry["id"]
    target = entry["target_total"]

    # Show current values
    if target == -1:
        current_ui.print_line(f"Editing {entry['name']} (Not set)")
    else:
        current_ui.print_line(f"Editing {entry['name']} (target: {target})")

    # Target
    target_str = current_ui.prompt(f"Target total (Enter to keep): ").strip()
    if target_str:
        try:
            new_target = int(target_str)
            if new_target < 0:
                current_ui.print_line("Target must be >= 0.")
                current_ui.prompt("Press Enter to continue.")
                return

            # Check if lowering target
            if target > 0 and new_target < target:
                confirm = (
                    current_ui.prompt(f"WARNING: Reducing target from {target} to {new_target}. Continue? (y/n): ")
                    .strip()
                    .lower()
                )
                if confirm != "y":
                    current_ui.print_line("Cancelled.")
                    current_ui.prompt("Press Enter to continue.")
                    return

            _logic.edit_entry(entry_id, target_total=new_target)
            current_ui.print_line(f"Target updated to {new_target}.")

        except ValueError:
            current_ui.print_line("Invalid number.")
            current_ui.prompt("Press Enter to continue.")
            return

    # Interval type
    current_interval = entry.get("interval_type", "daily")
    interval_type = current_ui.prompt(f"Interval type (daily/n_days/weekly/monthly, Enter=keep): ").strip().lower()
    if interval_type and interval_type in ("daily", "n_days", "weekly", "monthly"):
        # Prompt for interval value
        if interval_type == "n_days":
            val = current_ui.prompt("Number of days: ").strip()
            if val and val.isdigit():
                _logic.edit_entry(entry_id, interval_type=interval_type, interval_value=val)
        elif interval_type == "weekly":
            val = current_ui.prompt("Weekday (0=Sat, 1=Sun, 2=Mon, ...): ").strip()
            if val and val.isdigit():
                _logic.edit_entry(entry_id, interval_type=interval_type, interval_value=val)
        elif interval_type == "monthly":
            val = current_ui.prompt("Days (comma-separated, e.g., 1,15): ").strip()
            if val:
                _logic.edit_entry(entry_id, interval_type=interval_type, interval_value=val)
        else:  # daily
            _logic.edit_entry(entry_id, interval_type=interval_type, interval_value=None)
        current_ui.print_line(f"Interval updated to {interval_type}.")
    elif interval_type:
        current_ui.print_line("Invalid interval type.")

    current_ui.prompt("Press Enter to continue.")
