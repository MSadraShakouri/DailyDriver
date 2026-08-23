"""Interactive forms for changing hygiene configuration."""

from dailydriver.ui.terminal_ui import current_ui


def add_hygiene_item(conn):
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
        """INSERT INTO hygiene_config
           (item, desired_interval_days, early_warning_enabled, show_due_today)
           VALUES (?,?,?,?)""",
        (item, interval, early_enabled, due_today_enabled),
    )
    conn.commit()
    current_ui.print_line("Added.")
    current_ui.prompt("Press Enter to continue.")


def edit_hygiene_item(conn):
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
        """UPDATE hygiene_config
           SET item = ?, desired_interval_days = ?, early_warning_enabled = ?, show_due_today = ?
           WHERE id = ?""",
        (new_name, interval, early_enabled, due_today_enabled, row["id"]),
    )
    conn.commit()
    current_ui.print_line("Updated.")
    current_ui.prompt("Press Enter to continue.")


def delete_hygiene_item(conn):
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
