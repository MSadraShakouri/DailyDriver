"""Interactive qada entry editor."""

from dailydriver.features.presentation import format_interval
from dailydriver.ui.terminal_ui import current_ui

from . import entries, overview


def edit_entry(choice):
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

    entries = overview.get_all_entries_with_progress()
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

            entries.edit_entry(entry_id, target_total=new_target)
            current_ui.print_line(f"Target updated to {new_target}.")

        except ValueError:
            current_ui.print_line("Invalid number.")
            current_ui.prompt("Press Enter to continue.")
            return

    # Interval type – show current display
    current_interval_display = format_interval(entry)
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
                entries.edit_entry(entry_id, interval_type=interval_type, interval_value=val)
                current_ui.print_line(f"Interval updated to every {val} days.")
            else:
                current_ui.print_line("Invalid value. Interval unchanged.")
        elif interval_type == "weekly":
            val = current_ui.prompt("Weekday (0=Sat, 1=Sun, 2=Mon, ...): ").strip()
            if val and val.isdigit():
                weekday_map = ["Saturday", "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                try:
                    weekday_name = weekday_map[int(val)]
                    entries.edit_entry(entry_id, interval_type=interval_type, interval_value=val)
                    current_ui.print_line(f"Interval updated to weekly on {weekday_name}.")
                except (ValueError, IndexError):
                    current_ui.print_line("Invalid weekday number.")
            else:
                current_ui.print_line("Invalid value. Interval unchanged.")
        elif interval_type == "monthly":
            val = current_ui.prompt("Days (comma-separated, e.g., 1,15): ").strip()
            if val:
                entries.edit_entry(entry_id, interval_type=interval_type, interval_value=val)
                current_ui.print_line(f"Interval updated to monthly on {val}.")
            else:
                current_ui.print_line("Invalid value. Interval unchanged.")
        else:  # daily
            entries.edit_entry(entry_id, interval_type=interval_type, interval_value=None)
            current_ui.print_line("Interval updated to daily.")
    else:
        current_ui.print_line("Interval unchanged.")

    current_ui.prompt("Press Enter to continue.")
