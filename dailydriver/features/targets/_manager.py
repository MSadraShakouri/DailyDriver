"""Interactive manager UI for targets feature."""

import jdatetime

from dailydriver.display.display_utils import spread_line, get_width
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.core.database import get_connection_cm

from . import _logic
from ._utils import get_daily_total, get_last_fulfilled_date


def show_manager(kind: str | None = None):
    """Main loop for the interactive targets manager.
    kind: 'nazr' or 'habit' to filter entries.
    """
    while True:
        current_ui.clear()
        current_ui.print_line("─── Targets Manager ───")
        if kind:
            current_ui.print_line(f"  Filter: {kind.upper()}")
        current_ui.print_line()

        # Fetch entries
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

        # Prepare table data
        today = jdatetime.date.today()
        rows = []
        for e in entries:
            # Compute next due date
            next_due = _logic.compute_next_due(e, today)

            # Determine due display
            if next_due is None:
                due_display = "-"
            elif next_due == today:
                due_display = "today"
            else:
                days = (next_due - today).days
                due_display = f"{days}d"

            # Progress display
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

            # Truncate name if too long
            name = e["name"]
            if len(name) > 12:
                name = name[:11] + "…"

            rows.append({
                "id": e["id"],
                "name": name,
                "prog": prog_display,
                "due": due_display,
                "status": status,
                "kind": e["kind"],
                "entry": e,
            })

        # Render table using spread_line
        tw = get_width()
        header_parts = [" #", "Name", "Progress", "Due", ""]
        header = spread_line(header_parts, width=tw, margins=0)
        current_ui.print_line(header)
        current_ui.print_line("─" * min(tw, 50))

        for row in rows:
            parts = [
                f"{row['id']}",
                row["name"],
                row["prog"],
                row["due"],
                row["status"],
            ]
            line = spread_line(parts, width=tw, margins=0)
            # Color complete entries green
            if row["status"] == "✅":
                line = f"\033[32m{line}\033[0m"
            # Dim paused entries
            elif row["status"] == "❄️":
                line = f"\033[2m{line}\033[0m"
            current_ui.print_line(line)

        current_ui.print_line()
        current_ui.print_line("(l)og <#> <amount>  (a)dd  (q)uit")

        choice = current_ui.prompt("> ").strip().lower()
        if choice == "q":
            break
        elif choice == "a":
            _add_entry_interactive(kind)
        elif choice.startswith("l "):
            _log_from_manager(choice, kind)
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
