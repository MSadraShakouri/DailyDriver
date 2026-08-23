"""Interactive hygiene interval manager."""

from dailydriver.core.database import get_connection_cm, get_last_hygiene_time
from dailydriver.core.day_start import get_shifted_today, shift_timestamp_to_date
from dailydriver.display.display_utils import get_width, spread_line
from dailydriver.display.header import build_header_data
from dailydriver.display.header_renderer import print_header
from dailydriver.ui.terminal_ui import current_ui

from .editor import add_hygiene_item, delete_hygiene_item, edit_hygiene_item


def manage_hygiene():
    """Interactive manager for hygiene intervals – table layout with dynamic columns."""
    with get_connection_cm() as conn:
        cur = conn.cursor()

        while True:
            current_ui.clear()

            # --- Header ---
            data = build_header_data()
            print_header(data)

            # --- Fetch data ---
            cur.execute(
                "SELECT id, item, desired_interval_days, early_warning_enabled, show_due_today "
                "FROM hygiene_config ORDER BY item"
            )
            items = cur.fetchall()

            if not items:
                current_ui.print_line("  No hygiene items configured.")
                current_ui.print_line()
                current_ui.print_line("  (a)dd  (q)uit")
                choice = current_ui.prompt("> ").strip().lower()
                if choice == "a":
                    add_hygiene_item(conn)
                elif choice == "q":
                    break
                continue

            # --- Compute rows and decide interval format ---
            rows = []

            # First pass: build rows with verbose interval format
            for row in items:
                item_id = row["id"]
                item = row["item"]
                interval = row["desired_interval_days"]

                last_time = get_last_hygiene_time(conn, item)
                if last_time:
                    last_shifted = shift_timestamp_to_date(last_time)
                    shifted_today = get_shifted_today()
                    days_since = (shifted_today - last_shifted).days
                else:
                    days_since = None
                days_left = interval - days_since if days_since is not None else None

                # Due state
                if days_left is None:
                    due_state = "-"
                elif days_left < 0:
                    due_state = "overdue"
                elif days_left == 0:
                    due_state = "today"
                elif days_left == 1:
                    due_state = "tomorrow"
                else:
                    due_state = f"in {days_left}d"

                # Interval display (verbose)
                if interval == 1:
                    interval_verbose = "1 day"
                else:
                    interval_verbose = f"{interval} days"

                rows.append(
                    {
                        "id": item_id,
                        "item": item,
                        "interval_verbose": interval_verbose,
                        "interval_short": f"{interval}d",
                        "due_state": due_state,
                        "days_left": days_left,
                        "early": "✓" if row["early_warning_enabled"] else "✗",
                        "due_today": "✓" if row["show_due_today"] else "✗",
                    }
                )

            # Determine terminal width and column widths
            tw = get_width()

            # Compute max widths with verbose interval first
            max_item = max((len(r["item"]) for r in rows), default=0)
            max_interval_verbose = max((len(r["interval_verbose"]) for r in rows), default=0)
            max_due = max((len(r["due_state"]) for r in rows), default=0)
            # Early and Due toggles are always 1 char
            max_early = 1
            max_due_today = 1

            # Calculate total needed width with verbose intervals
            # Columns: Item + Interval + Next + E + D + 8 spaces (between columns)
            total_needed = max_item + max_interval_verbose + max_due + max_early + max_due_today + 8

            # Choose interval format
            if total_needed <= tw:
                # Use verbose
                for r in rows:
                    r["interval"] = r["interval_verbose"]
                max_interval = max_interval_verbose
            else:
                # Use short
                for r in rows:
                    r["interval"] = r["interval_short"]
                max_interval = max((len(r["interval"]) for r in rows), default=0)

            # Update total needed after final interval format
            total_needed = max_item + max_interval + max_due + max_early + max_due_today + 8
            # If still too wide, we might shrink item column? But we never truncate item.
            # We'll let spread_line handle it, but it may be tight. We'll allow.

            rows.sort(key=lambda r: (r["days_left"] is None, r["days_left"] or 0, r["item"].lower()))

            # --- Render table ---
            header_parts = [
                " " + "Item".center(max_item),
                "Interval".center(max_interval),
                "Next".center(max_due),
                "E",
                "D" + " ",
            ]
            header = spread_line(header_parts, width=tw, margins=0)
            current_ui.print_line(header)
            current_ui.print_line("─" * tw)

            for r in rows:
                parts = [
                    " " + r["item"].ljust(max_item),
                    r["interval"].ljust(max_interval),
                    r["due_state"].ljust(max_due),
                    r["early"],
                    r["due_today"] + " ",
                ]
                line = spread_line(parts, width=tw, margins=0)

                # Color entire row
                if r["days_left"] is not None and r["days_left"] < 0:
                    line = f"\033[31m{line}\033[0m"  # red
                elif r["days_left"] is not None and r["days_left"] == 0:
                    line = f"\033[33m{line}\033[0m"  # yellow

                current_ui.print_line(line)

            current_ui.print_line()

            # --- Commands ---

            tw = get_width()
            line = spread_line(["(a)dd", "(e)dit", "(d)elete", "(q)uit"], width=tw, margins=1 / 8)
            current_ui.print_line(line)

            current_ui.print_line()
            choice = current_ui.prompt("> ").strip().lower()

            if choice == "q":
                break
            elif choice == "a":
                add_hygiene_item(conn)
            elif choice == "e":
                edit_hygiene_item(conn)
            elif choice == "d":
                delete_hygiene_item(conn)
            else:
                current_ui.print_line("Unknown command.")
                current_ui.prompt("Press Enter to continue.")
