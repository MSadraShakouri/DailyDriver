"""Interactive add, edit, and delete forms for targets."""

from dailydriver.ui.terminal_ui import current_ui

from . import entries


def add_entry(default_kind: str | None = None):
    """Interactive flow for adding a new target entry."""
    current_ui.print_line("\n─── Add New Target ───")

    if default_kind:
        kind = default_kind
        current_ui.print_line(f"Kind: {kind} (pre-set)")
    else:
        kind_prompt = "Kind (n)azr or (h)abit: "
        kind_choice = current_ui.prompt(kind_prompt).strip().lower()
        if kind_choice == "n":
            kind = "nazr"
        elif kind_choice == "h":
            kind = "habit"
        else:
            current_ui.print_line("Invalid kind. Cancelled.")
            return

    name = current_ui.prompt("Name: ").strip()
    if not name:
        current_ui.print_line("Name is required. Cancelled.")
        return

    target_str = current_ui.prompt("Target (Enter for indefinite): ").strip()
    if target_str:
        try:
            target_total = int(target_str)
            if target_total <= 0:
                current_ui.print_line("Target must be positive. Cancelled.")
                return
        except ValueError:
            current_ui.print_line("Invalid number. Cancelled.")
            return
    else:
        target_total = None

    interval_prompt = "Interval (d)aily, (w)eekly, (n)_days, or (s)kip: "
    interval_choice = current_ui.prompt(interval_prompt).strip().lower()
    interval_type = None
    interval_value = None

    if interval_choice == "d":
        interval_type = "daily"
        interval_value = 1
    elif interval_choice == "w":
        interval_type = "weekly"
        val = current_ui.prompt("Weekday (0=Sat, 1=Sun, ... 6=Fri): ").strip()
        if val and val.isdigit():
            interval_value = int(val)
            if not (0 <= interval_value <= 6):
                current_ui.print_line("Weekday must be 0-6. Cancelled.")
                return
        else:
            current_ui.print_line("Invalid weekday. Cancelled.")
            return
    elif interval_choice == "n":
        interval_type = "n_days"
        val = current_ui.prompt("Number of days: ").strip()
        if val and val.isdigit():
            interval_value = int(val)
            if interval_value <= 0:
                current_ui.print_line("Days must be positive. Cancelled.")
                return
        else:
            current_ui.print_line("Invalid number. Cancelled.")
            return
    elif interval_choice == "s":
        interval_type = None
        interval_value = None
    else:
        current_ui.print_line("Invalid interval choice. Cancelled.")
        return

    target_per_interval = None
    if interval_type:
        target_str = current_ui.prompt("Target per interval (Enter for 'any amount'): ").strip()
        if target_str:
            try:
                target_per_interval = int(target_str)
                if target_per_interval <= 0:
                    current_ui.print_line("Target per interval must be positive. Cancelled.")
                    return
            except ValueError:
                current_ui.print_line("Invalid number. Cancelled.")
                return

    try:
        eid = entries.add_entry(
            kind=kind,
            name=name,
            target_total=target_total,
            interval_type=interval_type,
            interval_value=interval_value,
            target_per_interval=target_per_interval,
        )
        current_ui.print_line(f"Added: {name} (ID: {eid})")
    except Exception as e:
        current_ui.print_line(f"Error: {e}")

    current_ui.prompt("Press Enter to continue.")


def edit_entry(choice: str):
    """Handle edit from the manager."""
    parts = choice.strip().split()
    if len(parts) < 2:
        current_ui.print_line("Usage: e <#>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        entry_id = int(parts[1])
    except ValueError:
        current_ui.print_line("ID must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries.get_entry_by_id(entry_id)
    if not entry:
        current_ui.print_line(f"Entry {entry_id} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    current_ui.print_line(f"\n─── Editing: {entry['name']} ───")
    current_ui.print_line("(Enter to keep current value)\n")

    current_ui.print_line(f"Name: {entry['name']}")
    name = current_ui.prompt("New name: ").strip()
    if name and name != entry["name"]:
        existing = entries.get_entry_by_name(name)
        if existing and existing["id"] != entry_id:
            current_ui.print_line(f"Name '{name}' already exists. Cancelled.")
            current_ui.prompt("Press Enter to continue.")
            return

    current_ui.print_line(f"Target: {entry['target_total'] or 'indefinite'}")
    target_str = current_ui.prompt("New target (Enter for indefinite): ").strip()
    if target_str:
        try:
            target_total = int(target_str)
            if target_total <= 0:
                current_ui.print_line("Target must be positive. Cancelled.")
                current_ui.prompt("Press Enter to continue.")
                return
        except ValueError:
            current_ui.print_line("Invalid number. Cancelled.")
            current_ui.prompt("Press Enter to continue.")
            return
    else:
        target_total = None

    current_ui.print_line(f"Interval: {entry.get('interval_type') or 'none'}")
    interval_prompt = "New interval (d)aily, (w)eekly, (n)_days, or (s)kip: "
    interval_choice = current_ui.prompt(interval_prompt).strip().lower()
    if interval_choice == "d":
        interval_type = "daily"
        interval_value = 1
    elif interval_choice == "w":
        interval_type = "weekly"
        val = current_ui.prompt("Weekday (0=Sat, 1=Sun, ... 6=Fri): ").strip()
        if val and val.isdigit():
            interval_value = int(val)
            if not (0 <= interval_value <= 6):
                current_ui.print_line("Weekday must be 0-6. Cancelled.")
                current_ui.prompt("Press Enter to continue.")
                return
        else:
            current_ui.print_line("Invalid weekday. Cancelled.")
            current_ui.prompt("Press Enter to continue.")
            return
    elif interval_choice == "n":
        interval_type = "n_days"
        val = current_ui.prompt("Number of days: ").strip()
        if val and val.isdigit():
            interval_value = int(val)
            if interval_value <= 0:
                current_ui.print_line("Days must be positive. Cancelled.")
                current_ui.prompt("Press Enter to continue.")
                return
        else:
            current_ui.print_line("Invalid number. Cancelled.")
            current_ui.prompt("Press Enter to continue.")
            return
    elif interval_choice == "s":
        interval_type = None
        interval_value = None
    else:
        interval_type = entry.get("interval_type")
        interval_value = entry.get("interval_value")

    current_ui.print_line(f"Target per interval: {entry.get('target_per_interval') or 'any amount'}")
    target_per_str = current_ui.prompt("New target per interval (Enter for 'any amount'): ").strip()
    if target_per_str:
        try:
            target_per_interval = int(target_per_str)
            if target_per_interval <= 0:
                current_ui.print_line("Target per interval must be positive. Cancelled.")
                current_ui.prompt("Press Enter to continue.")
                return
        except ValueError:
            current_ui.print_line("Invalid number. Cancelled.")
            current_ui.prompt("Press Enter to continue.")
            return
    else:
        target_per_interval = None

    updates = {}
    if name and name != entry["name"]:
        updates["name"] = name
    if target_str or target_str == "":
        updates["target_total"] = target_total
    if interval_type != entry.get("interval_type") or interval_value != entry.get("interval_value"):
        updates["interval_type"] = interval_type
        updates["interval_value"] = interval_value
    if target_per_str or target_per_str == "":
        updates["target_per_interval"] = target_per_interval

    if updates:
        result = entries.edit_entry(entry_id, **updates)
        current_ui.print_line(result)
    else:
        current_ui.print_line("No changes made.")

    current_ui.prompt("Press Enter to continue.")


def delete_entry(choice: str):
    """Handle delete from the manager."""
    parts = choice.strip().split()
    if len(parts) < 2:
        current_ui.print_line("Usage: d <#>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        entry_id = int(parts[1])
    except ValueError:
        current_ui.print_line("ID must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    entry = entries.get_entry_by_id(entry_id)
    if not entry:
        current_ui.print_line(f"Entry {entry_id} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    confirm = current_ui.prompt(f"Delete '{entry['name']}'? (y/n): ").strip().lower()
    if confirm != "y":
        current_ui.print_line("Cancelled.")
        current_ui.prompt("Press Enter to continue.")
        return

    result = entries.delete_entry(entry_id)
    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")
