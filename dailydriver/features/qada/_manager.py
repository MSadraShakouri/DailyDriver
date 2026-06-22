# dailydriver/features/qada/_manager.py
"""Interactive qada manager."""

import textwrap

import jdatetime

from dailydriver.display.display_utils import display_width, get_width, pline_wrap, spread_line
from dailydriver.display.header import build_header_data
from dailydriver.display.header_renderer import print_header
from dailydriver.features.qada import _logic
from dailydriver.ui.terminal_ui import current_ui


def show_qada_manager():
    """Main loop for the qada manager."""
    while True:
        current_ui.clear()
        # Show header like hygiene
        data = build_header_data()
        print_header(data)

        entries = _logic.get_all_entries_with_progress()

        # Render table (no extra blank line before it)
        _render_entries(entries)

        # Command guide – two lines spread across 2/3 of screen
        current_ui.print_line()  # breather before commands
        _print_commands()

        # Breather before prompt
        current_ui.print_line()
        choice = current_ui.prompt("> ").strip().lower()

        if choice == "q":
            break
        elif choice == "?":
            _show_help()
            current_ui.prompt("Press Enter to continue.")
        elif choice.startswith("l "):
            _log_entry(choice)
        elif choice.startswith("p "):
            _pause_entry(choice)
        elif choice.startswith("e "):
            _edit_entry(choice)
        else:
            current_ui.print_line("Unknown command. Type ? for help.")
            current_ui.prompt("Press Enter to continue.")


def _print_commands():
    """Print the command guide using spread_line."""
    tw = get_width()

    # Line 1: l and p
    line1_parts = ["l <#> log progress", "p <#> pause/unpause"]
    # Pad each to same width? No – spread_line handles distribution
    line1 = spread_line(line1_parts, width=tw, margins=1 / 8)
    current_ui.print_line(line1)

    # Line 2: e, ?, q
    line2_parts = ["e <#> edit", "? help", "q quit"]
    line2 = spread_line(line2_parts, width=tw, margins=1 / 8)
    current_ui.print_line(line2)


def _show_help():
    """Show help screen inside the manager."""
    current_ui.print_line("\n┌─ Qada Manager Help ───────────────────────────┐")
    current_ui.print_line("│ l <#>  - Log progress for entry #              │")
    current_ui.print_line("│ p <#>  - Pause/unpause entry #                 │")
    current_ui.print_line("│ e <#>  - Edit entry # (target/interval)        │")
    current_ui.print_line("│ ?      - Show this help                        │")
    current_ui.print_line("│ q      - Quit manager                          │")
    current_ui.print_line("└─────────────────────────────────────────────────┘")


def _smart_percent(value):
    """Format percentage smartly: 0% for zero, remove trailing zeros."""
    if value == 0:
        return "0%"
    # Format with up to 2 decimal places, strip trailing zeros and decimal
    s = f"{value:.2f}".rstrip("0").rstrip(".")
    return f"{s}%"


def _format_next_due(next_instance, today):
    """Format next due as 'today', 'tomorrow', or 'in X days'."""
    if next_instance is None:
        return "-"
    days = (next_instance - today).days
    if days == 0:
        return "today"
    elif days == 1:
        return "tomorrow"
    else:
        return f"in {days} days"


def _format_interval_display(entry):
    """Return human-readable interval string."""
    itype = entry.get("interval_type", "daily")
    ival = entry.get("interval_value")
    if itype == "daily":
        return "daily"
    elif itype == "n_days":
        return f"every {ival} days"
    elif itype == "weekly":
        weekday_map = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        try:
            return f"weekly on {weekday_map[int(ival)]}"
        except (ValueError, TypeError, IndexError):
            return f"weekly on {ival}"
    elif itype == "monthly":
        return f"monthly on {ival}"
    return itype


def _render_entries(entries):
    """Render the qada entries table using spread_line."""
    tw = get_width()
    today_j = jdatetime.date.today()

    # Prepare all row data and track max widths
    rows = []
    max_name = display_width("Name")
    max_prog = display_width("Progress")
    max_pct = display_width("%")
    max_next = display_width("Next")

    for entry in entries:
        idx = str(entry["index"])
        name = entry["name"]
        prog = entry["progress_display"]

        pct_display = ""
        target = entry["target_total"]
        if target != -1 and entry["percentage"] is not None:
            pct_display = _smart_percent(entry["percentage"])

        next_display = _format_next_due(entry["next_instance"], today_j)

        max_name = max(max_name, display_width(name))
        max_prog = max(max_prog, display_width(prog))
        max_pct = max(max_pct, display_width(pct_display))
        max_next = max(max_next, display_width(next_display))

        rows.append(
            {
                "idx": idx,
                "name": name,
                "prog": prog,
                "pct": pct_display,
                "next": next_display,
                "target": target,
                "is_complete": entry["is_complete"],
                "is_paused": entry["is_paused"],
            }
        )

    # Build header with padded columns
    header_parts = [
        " " + "#".center(1),
        "Name".center(max_name),
        "Progress".center(max_prog),
        "%".center(max_pct),
        "Next".center(max_next) + " ",
    ]
    header = spread_line(header_parts, width=tw, margins=0)
    current_ui.print_line(header)
    current_ui.print_line("─" * tw)

    # Render rows
    for row in rows:
        parts = [
            " " + row["idx"].ljust(1),
            row["name"].ljust(max_name),
            row["prog"].ljust(max_prog),
            row["pct"].ljust(max_pct),
            row["next"].ljust(max_next) + " ",
        ]
        line = spread_line(parts, width=tw, margins=0)

        # Apply colors
        target = row["target"]
        if target == -1:
            line = f"\033[33m{line}\033[0m"
        elif row["is_complete"]:
            line = f"\033[32m{line}\033[0m"
        elif row["is_paused"]:
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

    amount_str = current_ui.prompt("Amount to log (Enter=1): ").strip()
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
    target_str = current_ui.prompt("Target total (Enter to keep): ").strip()
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

    # Interval type – show current display
    current_interval_display = _format_interval_display(entry)
    current_interval = entry.get("interval_type", "daily")

    current_ui.print_line(f"\nCurrent interval: {current_interval_display}")
    current_ui.print_line("\nInterval options:")
    current_ui.print_line("  1. daily     - every day")
    current_ui.print_line("  2. n_days    - every N days (e.g., 3)")
    current_ui.print_line("  3. weekly    - specific weekday (0=Sat, 1=Sun, ...)")
    current_ui.print_line("  4. monthly   - specific days (e.g., 1,15)")

    choice = current_ui.prompt("Choose (1-4, Enter to keep): ").strip()

    if choice == "":
        interval_type = current_interval
    elif choice == "1":
        interval_type = "daily"
    elif choice == "2":
        interval_type = "n_days"
    elif choice == "3":
        interval_type = "weekly"
    elif choice == "4":
        interval_type = "monthly"
    else:
        current_ui.print_line("Invalid choice.")
        current_ui.prompt("Press Enter to continue.")
        return

    if interval_type != current_interval:
        # Prompt for interval value based on type
        if interval_type == "n_days":
            val = current_ui.prompt("Number of days: ").strip()
            if val and val.isdigit():
                _logic.edit_entry(entry_id, interval_type=interval_type, interval_value=val)
                current_ui.print_line(f"Interval updated to every {val} days.")
            else:
                current_ui.print_line("Invalid value. Interval unchanged.")
        elif interval_type == "weekly":
            val = current_ui.prompt("Weekday (0=Sat, 1=Sun, 2=Mon, ...): ").strip()
            if val and val.isdigit():
                weekday_map = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                try:
                    weekday_name = weekday_map[int(val)]
                    _logic.edit_entry(entry_id, interval_type=interval_type, interval_value=val)
                    current_ui.print_line(f"Interval updated to weekly on {weekday_name}.")
                except (ValueError, IndexError):
                    current_ui.print_line("Invalid weekday number.")
            else:
                current_ui.print_line("Invalid value. Interval unchanged.")
        elif interval_type == "monthly":
            val = current_ui.prompt("Days (comma-separated, e.g., 1,15): ").strip()
            if val:
                _logic.edit_entry(entry_id, interval_type=interval_type, interval_value=val)
                current_ui.print_line(f"Interval updated to monthly on {val}.")
            else:
                current_ui.print_line("Invalid value. Interval unchanged.")
        else:  # daily
            _logic.edit_entry(entry_id, interval_type=interval_type, interval_value=None)
            current_ui.print_line("Interval updated to daily.")
    else:
        current_ui.print_line("Interval unchanged.")

    current_ui.prompt("Press Enter to continue.")
