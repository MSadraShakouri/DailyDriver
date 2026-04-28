from dailydriver.core.database import get_connection_cm
from dailydriver.ui.terminal_ui import current_ui

def manage_hygiene():
    with get_connection_cm() as conn:
        cur = conn.cursor()
        while True:
            cur.execute("SELECT id, item, desired_interval_days, early_warning_enabled, show_due_today FROM hygiene_config ORDER BY item")
            items = cur.fetchall()
            current_ui.print_line("\n── Hygiene Intervals ──")
            if not items:
                current_ui.print_line("No hygiene items configured yet.")
            for row in items:
                early_str = 'on' if row['early_warning_enabled'] else 'off'
                due_str = 'on' if row['show_due_today'] else 'off'
                current_ui.print_line(f"  {row['item']}: every {row['desired_interval_days']} day(s) | early: {early_str} | due today: {due_str}")
            current_ui.print_line("\n(a)dd  (e)dit  (d)elete  (q)uit")
            choice = current_ui.prompt("> ").strip().lower()
            if choice == 'q':
                break
            elif choice == 'a':
                item = current_ui.prompt("Item name (e.g., shaving, brushing_teeth): ").strip().lower()
                if not item:
                    continue
                try:
                    days = int(current_ui.prompt("Desired interval (days): "))
                    if days < 1:
                        raise ValueError
                except ValueError:
                    current_ui.print_line("Invalid number.")
                    continue
                # check if exists
                cur.execute("SELECT id FROM hygiene_config WHERE item=?", (item,))
                if cur.fetchone():
                    current_ui.print_line("Item already exists. Use edit.")
                    continue

                # early warning prompt (Enter=yes, n=no)
                ew = current_ui.prompt("Early warning? (Enter=yes, n=no): ").strip().lower()
                early_enabled = 0 if ew == 'n' else 1

                # due today prompt
                dt = current_ui.prompt("Show due today? (Enter=yes, n=no): ").strip().lower()
                due_today_enabled = 0 if dt == 'n' else 1

                cur.execute(
                    "INSERT INTO hygiene_config (item, desired_interval_days, early_warning_enabled, show_due_today) VALUES (?,?,?,?)",
                    (item, days, early_enabled, due_today_enabled)
                )
                conn.commit()
                current_ui.print_line("Added.")
            elif choice == 'e':
                if not items:
                    continue
                item_name = current_ui.prompt("Item name to edit: ").strip().lower()
                cur.execute("SELECT id, desired_interval_days, early_warning_enabled, show_due_today FROM hygiene_config WHERE item=?", (item_name,))
                row = cur.fetchone()
                if not row:
                    current_ui.print_line("Not found.")
                    continue
                current_ui.print_line(f"Current: interval={row['desired_interval_days']}d, early={'on' if row['early_warning_enabled'] else 'off'}, due today={'on' if row['show_due_today'] else 'off'}")

                days_str = current_ui.prompt("New interval (days, Enter=keep): ").strip()
                if days_str:
                    try:
                        days = int(days_str)
                    except ValueError:
                        current_ui.print_line("Invalid number.")
                        continue
                else:
                    days = row['desired_interval_days']

                # early warning toggle
                current_ew = row['early_warning_enabled']
                ew_str = current_ui.prompt(f"Early warning? [currently {'on' if current_ew else 'off'}] (Enter=keep, n=toggle): ").strip().lower()
                if ew_str == 'n':
                    early_enabled = 0 if current_ew else 1
                else:
                    early_enabled = current_ew

                # due today toggle
                current_dt = row['show_due_today']
                dt_str = current_ui.prompt(f"Show due today? [currently {'on' if current_dt else 'off'}] (Enter=keep, n=toggle): ").strip().lower()
                if dt_str == 'n':
                    due_today_enabled = 0 if current_dt else 1
                else:
                    due_today_enabled = current_dt

                cur.execute(
                    "UPDATE hygiene_config SET desired_interval_days=?, early_warning_enabled=?, show_due_today=? WHERE item=?",
                    (days, early_enabled, due_today_enabled, item_name)
                )
                conn.commit()
                current_ui.print_line("Updated.")
            elif choice == 'd':
                item_name = current_ui.prompt("Item name to delete: ").strip().lower()
                cur.execute("DELETE FROM hygiene_config WHERE item=?", (item_name,))
                conn.commit()
                current_ui.print_line("Deleted.")
