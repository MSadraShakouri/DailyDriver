# dailydriver/features/hygiene/_logic.py

import time
from datetime import datetime

import jdatetime

from dailydriver.core.database import get_connection_cm, get_last_hygiene_time
from dailydriver.core.day_start import get_shifted_today, shift_timestamp_to_date
from dailydriver.display.display_utils import get_width, spread_line
from dailydriver.display.header import build_header_data
from dailydriver.display.header_renderer import print_header
from dailydriver.ui.terminal_ui import current_ui


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
                    _add_hygiene_item(conn)
                elif choice == "q":
                    break
                continue

            # --- Compute rows and decide interval format ---
            now_ts = int(time.time())
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
                _add_hygiene_item(conn)
            elif choice == "e":
                _edit_hygiene_item(conn)
            elif choice == "d":
                _delete_hygiene_item(conn)
            else:
                current_ui.print_line("Unknown command.")
                current_ui.prompt("Press Enter to continue.")


def _add_hygiene_item(conn):
    """Interactive add flow."""
    current_ui.print_line("\n─── Add Hygiene Item ───")

    item = current_ui.prompt("Item name: ").strip().lower()
    if not item:
        current_ui.print_line("Item name is required.")
        current_ui.prompt("Press Enter to continue.")
        return

    # Check if already exists
    cur = conn.cursor()
    cur.execute("SELECT id FROM hygiene_config WHERE item = ?", (item,))
    if cur.fetchone():
        current_ui.print_line(f"Item '{item}' already exists.")
        current_ui.prompt("Press Enter to continue.")
        return

    interval_str = current_ui.prompt("Desired interval (days): ").strip()
    try:
        interval = int(interval_str)
        if interval < 1:
            raise ValueError
    except ValueError:
        current_ui.print_line("Invalid interval. Must be a positive number.")
        current_ui.prompt("Press Enter to continue.")
        return

    # Early warning prompt (Enter=yes, n=no)
    ew = current_ui.prompt("Early warning? (Enter=yes, n=no): ").strip().lower()
    early_enabled = 0 if ew == "n" else 1

    # Due today prompt (Enter=yes, n=no)
    dt = current_ui.prompt("Show due today? (Enter=yes, n=no): ").strip().lower()
    due_today_enabled = 0 if dt == "n" else 1

    cur.execute(
        "INSERT INTO hygiene_config (item, desired_interval_days, early_warning_enabled, show_due_today) VALUES (?,?,?,?)",
        (item, interval, early_enabled, due_today_enabled),
    )
    conn.commit()
    current_ui.print_line("Added.")
    current_ui.prompt("Press Enter to continue.")


def _edit_hygiene_item(conn):
    """Interactive edit flow with Enter=keep."""
    cur = conn.cursor()
    item_name = current_ui.prompt("Item name to edit: ").strip().lower()
    if not item_name:
        current_ui.print_line("Item name is required.")
        current_ui.prompt("Press Enter to continue.")
        return

    cur.execute(
        "SELECT id, item, desired_interval_days, early_warning_enabled, show_due_today "
        "FROM hygiene_config WHERE item = ?",
        (item_name,),
    )
    row = cur.fetchone()
    if not row:
        current_ui.print_line(f"Item '{item_name}' not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    current_ui.print_line(f"\n─── Editing: {row['item']} ───")
    current_ui.print_line("(Enter to keep current value)\n")

    # Item name
    current_ui.print_line(f"Name: {row['item']}")
    new_name = current_ui.prompt("New name: ").strip().lower()
    if new_name and new_name != row["item"]:
        # Check if name already taken
        cur.execute("SELECT id FROM hygiene_config WHERE item = ?", (new_name,))
        if cur.fetchone():
            current_ui.print_line(f"Name '{new_name}' already exists. Using current name.")
            new_name = row["item"]
    else:
        new_name = row["item"]

    # Interval
    current_ui.print_line(f"Interval: {row['desired_interval_days']} days")
    interval_str = current_ui.prompt("New interval (days): ").strip()
    if interval_str:
        try:
            interval = int(interval_str)
            if interval < 1:
                raise ValueError
        except ValueError:
            current_ui.print_line("Invalid interval. Keeping current.")
            interval = row["desired_interval_days"]
    else:
        interval = row["desired_interval_days"]

    # Early warning toggle
    current_ew = row["early_warning_enabled"]
    ew_prompt = f"Early warning? [currently {'on' if current_ew else 'off'}] (Enter=keep, n=toggle): "
    ew_choice = current_ui.prompt(ew_prompt).strip().lower()
    if ew_choice == "n":
        early_enabled = 0 if current_ew else 1
    else:
        early_enabled = current_ew

    # Due today toggle
    current_dt = row["show_due_today"]
    dt_prompt = f"Show due today? [currently {'on' if current_dt else 'off'}] (Enter=keep, n=toggle): "
    dt_choice = current_ui.prompt(dt_prompt).strip().lower()
    if dt_choice == "n":
        due_today_enabled = 0 if current_dt else 1
    else:
        due_today_enabled = current_dt

    # Update
    cur.execute(
        "UPDATE hygiene_config SET item = ?, desired_interval_days = ?, early_warning_enabled = ?, show_due_today = ? WHERE id = ?",
        (new_name, interval, early_enabled, due_today_enabled, row["id"]),
    )
    conn.commit()
    current_ui.print_line("Updated.")
    current_ui.prompt("Press Enter to continue.")


def _delete_hygiene_item(conn):
    """Interactive delete with confirmation."""
    cur = conn.cursor()
    item_name = current_ui.prompt("Item name to delete: ").strip().lower()
    if not item_name:
        current_ui.print_line("Item name is required.")
        current_ui.prompt("Press Enter to continue.")
        return

    cur.execute("SELECT id FROM hygiene_config WHERE item = ?", (item_name,))
    row = cur.fetchone()
    if not row:
        current_ui.print_line(f"Item '{item_name}' not found.")
        current_ui.prompt("Press Enter to continue.")
        return

    confirm = current_ui.prompt(f"Delete '{item_name}'? (y/n): ").strip().lower()
    if confirm != "y":
        current_ui.print_line("Cancelled.")
        current_ui.prompt("Press Enter to continue.")
        return

    cur.execute("DELETE FROM hygiene_config WHERE item = ?", (item_name,))
    conn.commit()
    current_ui.print_line("Deleted.")
    current_ui.prompt("Press Enter to continue.")
