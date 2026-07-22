"""Interactive manager UI for targets feature."""

import jdatetime

from dailydriver.display.display_utils import spread_line, get_width
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.core.database import get_connection_cm

from . import _logic
from ._utils import get_daily_total, get_last_fulfilled_date


def show_manager(kind: str | None = None):
    """Main loop for the interactive targets manager."""
    while True:
        current_ui.clear()
        current_ui.print_line("─── Targets Manager ───")
        if kind:
            current_ui.print_line(f"  Filter: {kind.upper()}")
        current_ui.print_line()

        entries = _logic.get_all_entries(kind=kind)
        if not entries:
            current_ui.print_line("  No entries found.")
            current_ui.print_line()
            current_ui.print_line("  (a)dd  (q)uit")
            choice = current_ui.prompt("> ").strip().lower()
            if choice == "a":
                _add_entry_interactive(kind)
            elif choice == "q":
                break
            continue

        today = jdatetime.date.today()
        rows = []
        for e in entries:
            next_due = _logic.compute_next_due(e, today)

            if next_due is None:
                due_display = "-"
            elif next_due == today:
                due_display = "today"
            else:
                days = (next_due - today).days
                due_display = f"{days}d"

            target = e["target_total"]
            logged = e["logged_total"]
            if target is not None:
                prog_display = f"{logged}/{target}"
            else:
                prog_display = f"{logged}/∞"

            # Status
            if target is not None and logged >= target:
                status = "✅"
            elif e.get("paused_until"):
                try:
                    y, m, d = map(int, e["paused_until"].split("-"))
                    pause_date = jdatetime.date(y, m, d)
                    if pause_date >= today:
                        status = "❄️"
                    else:
                        status = "-"
                except (ValueError, TypeError):
                    status = "-"
            else:
                status = "-"

            name = e["name"]
            if len(name) > 12:
                name = name[:11] + "…"

            rows.append({
                "id": e["id"],
                "name": name,
                "prog": prog_display,
                "due": due_display,
                "status": status,
                "entry": e,
            })

        tw = get_width()
        header_parts = [" #", "Name", "Progress", "Due", ""]
        header = spread_line(header_parts, width=tw, margins=0)
        current_ui.print_line(header)
        current_ui.print_line("─" * min(tw, 50))

        for row in rows:
            parts = [
                str(row["id"]),
                row["name"],
                row["prog"],
                row["due"],
                row["status"],
            ]
            line = spread_line(parts, width=tw, margins=0)
            if row["status"] == "✅":
                line = f"\033[32m{line}\033[0m"
            elif row["status"] == "❄️":
                line = f"\033[2m{line}\033[0m"
            current_ui.print_line(line)

        current_ui.print_line()
        current_ui.print_line("(l)og <#> <amount>  (p)ause <#>  (e)dit <#>  (d)elete <#>  (a)dd  (q)uit")

        choice = current_ui.prompt("> ").strip().lower()
        if choice == "q":
            break
        elif choice == "a":
            _add_entry_interactive(kind)
        elif choice.startswith("l "):
            _log_from_manager(choice, kind)
        elif choice.startswith("p "):
            _pause_from_manager(choice)
        elif choice.startswith("e "):
            _edit_from_manager(choice)
        elif choice.startswith("d "):
            _delete_from_manager(choice)
        else:
            current_ui.print_line("Unknown command.")
            current_ui.prompt("Press Enter to continue.")


def _add_entry_interactive(default_kind: str | None = None):
    """Interactive flow for adding a new target entry."""
    current_ui.print_line("\n─── Add New Target ───")

    # Kind
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

    # Name
    name = current_ui.prompt("Name: ").strip()
    if not name:
        current_ui.print_line("Name is required. Cancelled.")
        return

    # Target
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

    # Interval
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

    # Target per interval
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

    # Add the entry
    try:
        eid = _logic.add_entry(
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


def _log_from_manager(choice: str, kind: str | None = None):
    """Handle logging from the manager."""
    parts = choice.strip().split()
    if len(parts) < 3:
        current_ui.print_line("Usage: l <#> <amount>")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        identifier = int(parts[1])
    except ValueError:
        current_ui.print_line("ID must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        amount = int(parts[2])
    except ValueError:
        current_ui.print_line("Amount must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    if amount <= 0:
        current_ui.print_line("Amount must be positive.")
        current_ui.prompt("Press Enter to continue.")
        return

    # Get entry by ID
    entry = _logic.get_entry_by_id(identifier)
    if not entry:
        current_ui.print_line(f"Entry {identifier} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    # Check kind mismatch
    if kind and entry["kind"] != kind:
        current_ui.print_line(f"'{entry['name']}' is a {entry['kind']}, not a {kind}.")
        current_ui.prompt("Press Enter to continue.")
        return

    # Log
    result = _logic.log_progress(entry["name"], amount, expected_kind=kind)
    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")


def _pause_from_manager(choice: str):
    """Handle pause/unpause from the manager."""
    parts = choice.strip().split()
    if len(parts) < 2:
        current_ui.print_line("Usage: p <#> [days]")
        current_ui.prompt("Press Enter to continue.")
        return

    try:
        entry_id = int(parts[1])
    except ValueError:
        current_ui.print_line("ID must be a number.")
        current_ui.prompt("Press Enter to continue.")
        return

    days = None
    if len(parts) >= 3:
        try:
            days = int(parts[2])
            if days <= 0:
                current_ui.print_line("Days must be positive.")
                current_ui.prompt("Press Enter to continue.")
                return
        except ValueError:
            current_ui.print_line("Days must be a number.")
            current_ui.prompt("Press Enter to continue.")
            return

    result = _logic.toggle_pause(entry_id, days)
    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")


def _edit_from_manager(choice: str):
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

    entry = _logic.get_entry_by_id(entry_id)
    if not entry:
        current_ui.print_line(f"Entry {entry_id} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    current_ui.print_line(f"\n─── Editing: {entry['name']} ───")
    current_ui.print_line("(Enter to keep current value)\n")

    # Name
    current_ui.print_line(f"Name: {entry['name']}")
    name = current_ui.prompt("New name: ").strip()
    if name and name != entry["name"]:
        # Check for duplicate
        existing = _logic.get_entry_by_name(name)
        if existing and existing["id"] != entry_id:
            current_ui.print_line(f"Name '{name}' already exists. Cancelled.")
            current_ui.prompt("Press Enter to continue.")
            return

    # Target
    current_ui.print_line(f"Target: {entry['target_total']}")
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

    # Interval type
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
        # Keep current
        interval_type = entry.get("interval_type")
        interval_value = entry.get("interval_value")

    # Target per interval
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

    # Apply updates
    updates = {}
    if name and name != entry["name"]:
        updates["name"] = name
    if target_str:
        updates["target_total"] = target_total
    elif target_str == "" and entry["target_total"] is not None:
        updates["target_total"] = None
    if interval_type != entry.get("interval_type") or interval_value != entry.get("interval_value"):
        updates["interval_type"] = interval_type
        updates["interval_value"] = interval_value
    if target_per_str or (target_per_str == "" and entry.get("target_per_interval") is not None):
        updates["target_per_interval"] = target_per_interval

    if updates:
        result = _logic.edit_entry(entry_id, **updates)
        current_ui.print_line(result)
    else:
        current_ui.print_line("No changes made.")

    current_ui.prompt("Press Enter to continue.")


def _delete_from_manager(choice: str):
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

    entry = _logic.get_entry_by_id(entry_id)
    if not entry:
        current_ui.print_line(f"Entry {entry_id} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    confirm = current_ui.prompt(f"Delete '{entry['name']}'? (y/n): ").strip().lower()
    if confirm != "y":
        current_ui.print_line("Cancelled.")
        current_ui.prompt("Press Enter to continue.")
        return

    result = _logic.delete_entry(entry_id)
    current_ui.print_line(result)
    current_ui.prompt("Press Enter to continue.")
