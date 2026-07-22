"""Interactive manager UI for targets feature."""

import jdatetime

from dailydriver.display.display_utils import display_width, get_width, spread_line
from dailydriver.ui.terminal_ui import current_ui

from . import _logic



from dailydriver.display.header import build_header_data
from dailydriver.display.header_renderer import print_header

def show_manager(kind: str | None = None):
    while True:
        current_ui.clear()
        # Show header like qada
        data = build_header_data()
        print_header(data)

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

        _render_entries(entries)

        current_ui.print_line()  # breather before commands
        _print_commands()

        current_ui.print_line()
        choice = current_ui.prompt("> ").strip().lower()

        if choice == "q":
            break
        elif choice == "?":
            _show_help()
            current_ui.prompt("Press Enter to continue.")
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
            current_ui.print_line("Unknown command. Type ? for help.")
            current_ui.prompt("Press Enter to continue.")


def _print_commands():
    """Print the command guide using spread_line."""
    tw = get_width()

    line1_parts = ["l <#> <amount> log", "a add"]
    line1 = spread_line(line1_parts, width=tw, margins=1/8)
    current_ui.print_line(line1)

    line2_parts = ["p <#> pause/unpause", "e <#> edit"]
    line2 = spread_line(line2_parts, width=tw, margins=1/8)
    current_ui.print_line(line2)

    line3_parts = ["d <#> delete", "? help", "q quit"]
    line3 = spread_line(line3_parts, width=tw, margins=1/8)
    current_ui.print_line(line3)


def _show_help():
    """Show help screen inside the manager."""
    current_ui.print_line("\n┌─ Targets Manager Help ─────────────────────────┐")
    current_ui.print_line("│ l <#> <amount>  - Log progress for entry #      │")
    current_ui.print_line("│ p <#>           - Pause/unpause entry #         │")
    current_ui.print_line("│ e <#>           - Edit entry #                  │")
    current_ui.print_line("│ d <#>           - Delete entry #                │")
    current_ui.print_line("│ a               - Add new entry                 │")
    current_ui.print_line("│ ?               - Show this help                │")
    current_ui.print_line("│ q               - Quit manager                  │")
    current_ui.print_line("└─────────────────────────────────────────────────┘")


def _smart_percent(value):
    """Format percentage smartly: 0% for zero, remove trailing zeros."""
    if value == 0:
        return "0%"
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


def _render_entries(entries):
    """Render the targets entries table using spread_line."""
    tw = get_width()
    today_j = jdatetime.date.today()

    rows = []
    max_name = display_width("Name")
    max_prog = display_width("Progress")
    max_pct = display_width("%")
    max_next = display_width("Next")

    for entry in entries:
        idx = str(entry["id"])
        name = entry["name"]

        target = entry["target_total"]
        logged = entry["logged_total"]
 
        if target is not None:
            prog = f"{logged:,}/{target:,}"
        else:
            prog = f"{logged:,}/∞"

        pct_display = ""
        if target is not None and target > 0:
            pct_display = _smart_percent((logged / target) * 100)

        next_due = _logic.compute_next_due(entry, today_j)
        next_display = _format_next_due(next_due, today_j)

        max_name = max(max_name, display_width(name))
        max_prog = max(max_prog, display_width(prog))
        max_pct = max(max_pct, display_width(pct_display))
        max_next = max(max_next, display_width(next_display))

        rows.append({
            "idx": idx,
            "name": name,
            "prog": prog,
            "pct": pct_display,
            "next": next_display,
            "target": target,
            "logged": logged,
            "is_complete": target is not None and logged >= target,
            "is_paused": _is_paused(entry, today_j),
            "has_interval": entry.get("interval_type") is not None,
        })

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

    for row in rows:
        parts = [
            " " + row["idx"].ljust(1),
            row["name"].ljust(max_name),
            row["prog"].ljust(max_prog),
            row["pct"].ljust(max_pct),
            row["next"].ljust(max_next) + " ",
        ]
        line = spread_line(parts, width=tw, margins=0)

        if row["is_complete"]:
            line = f"\033[32m{line}\033[0m"
        elif row["is_paused"]:
            line = f"\033[2m{line}\033[0m"
        elif row["target"] is None:
            # Indefinite habit — shows as normal, no special color
            pass

        current_ui.print_line(line)


def _is_paused(entry, today):
    """Return True if the entry is paused on today."""
    paused_until = entry.get("paused_until")
    if not paused_until:
        return False
    try:
        y, m, d = map(int, paused_until.split("-"))
        pause_date = jdatetime.date(y, m, d)
        return pause_date >= today
    except (ValueError, TypeError):
        return False


def _add_entry_interactive(default_kind: str | None = None):
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

    entry = _logic.get_entry_by_id(identifier)
    if not entry:
        current_ui.print_line(f"Entry {identifier} not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    if kind and entry["kind"] != kind:
        current_ui.print_line(f"'{entry['name']}' is a {entry['kind']}, not a {kind}.")
        current_ui.prompt("Press Enter to continue.")
        return

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

    current_ui.print_line(f"Name: {entry['name']}")
    name = current_ui.prompt("New name: ").strip()
    if name and name != entry["name"]:
        existing = _logic.get_entry_by_name(name)
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
