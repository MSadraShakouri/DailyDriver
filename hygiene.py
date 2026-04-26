from database import get_connection

def manage_hygiene():
    """List hygiene config and allow setting/editing intervals."""
    conn = get_connection()
    cur = conn.cursor()
    while True:
        cur.execute("SELECT id, item, desired_interval_days, early_warning_enabled, show_due_today FROM hygiene_config ORDER BY item")
        items = cur.fetchall()
        print("\n── Hygiene Intervals ──")
        if not items:
            print("No hygiene items configured yet.")
        for row in items:
            early_str = 'on' if row['early_warning_enabled'] else 'off'
            due_str = 'on' if row['show_due_today'] else 'off'
            print(f"  {row['item']}: every {row['desired_interval_days']} day(s) | early: {early_str} | due today: {due_str}")
        print("\n(a)dd  (e)dit  (d)elete  (q)uit")
        choice = input("> ").strip().lower()
        if choice == 'q':
            break
        elif choice == 'a':
            item = input("Item name (e.g., shaving, brushing_teeth): ").strip().lower()
            if not item:
                continue
            try:
                days = int(input("Desired interval (days): "))
                if days < 1:
                    raise ValueError
            except ValueError:
                print("Invalid number.")
                continue
            # check if exists
            cur.execute("SELECT id FROM hygiene_config WHERE item=?", (item,))
            if cur.fetchone():
                print("Item already exists. Use edit.")
                continue

            # early warning prompt (Enter=yes, n=no)
            ew = input("Early warning? (Enter=yes, n=no): ").strip().lower()
            early_enabled = 0 if ew == 'n' else 1

            # due today prompt
            dt = input("Show due today? (Enter=yes, n=no): ").strip().lower()
            due_today_enabled = 0 if dt == 'n' else 1

            cur.execute(
                "INSERT INTO hygiene_config (item, desired_interval_days, early_warning_enabled, show_due_today) VALUES (?,?,?,?)",
                (item, days, early_enabled, due_today_enabled)
            )
            conn.commit()
            print("Added.")
        elif choice == 'e':
            if not items:
                continue
            item_name = input("Item name to edit: ").strip().lower()
            cur.execute("SELECT id, desired_interval_days, early_warning_enabled, show_due_today FROM hygiene_config WHERE item=?", (item_name,))
            row = cur.fetchone()
            if not row:
                print("Not found.")
                continue
            print(f"Current: interval={row['desired_interval_days']}d, early={'on' if row['early_warning_enabled'] else 'off'}, due today={'on' if row['show_due_today'] else 'off'}")

            days_str = input("New interval (days, Enter=keep): ").strip()
            if days_str:
                try:
                    days = int(days_str)
                except ValueError:
                    print("Invalid number.")
                    continue
            else:
                days = row['desired_interval_days']

            # early warning toggle
            current_ew = row['early_warning_enabled']
            ew_str = input(f"Early warning? [currently {'on' if current_ew else 'off'}] (Enter=keep, n=toggle): ").strip().lower()
            if ew_str == 'n':
                early_enabled = 0 if current_ew else 1
            else:
                early_enabled = current_ew

            # due today toggle
            current_dt = row['show_due_today']
            dt_str = input(f"Show due today? [currently {'on' if current_dt else 'off'}] (Enter=keep, n=toggle): ").strip().lower()
            if dt_str == 'n':
                due_today_enabled = 0 if current_dt else 1
            else:
                due_today_enabled = current_dt

            cur.execute(
                "UPDATE hygiene_config SET desired_interval_days=?, early_warning_enabled=?, show_due_today=? WHERE item=?",
                (days, early_enabled, due_today_enabled, item_name)
            )
            conn.commit()
            print("Updated.")
        elif choice == 'd':
            item_name = input("Item name to delete: ").strip().lower()
            cur.execute("DELETE FROM hygiene_config WHERE item=?", (item_name,))
            conn.commit()
            print("Deleted.")
    conn.close()
