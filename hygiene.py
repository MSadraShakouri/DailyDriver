from database import get_connection

def manage_hygiene():
    """List hygiene config and allow setting/editing intervals."""
    conn = get_connection()
    cur = conn.cursor()
    while True:
        cur.execute("SELECT id, item, desired_interval_days FROM hygiene_config ORDER BY item")
        items = cur.fetchall()
        print("\n── Hygiene Intervals ──")
        if not items:
            print("No hygiene items configured yet.")
        for row in items:
            print(f"  {row['item']}: every {row['desired_interval_days']} day(s)")
        print("\n(a)dd  (e)dit  (d)elete  (q)uit")
        choice = input("> ").strip().lower()
        if choice == 'q':
            break
        elif choice == 'a':
            item = input("Item name (e.g., shaving, brushing_teeth): ").strip()
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
            cur.execute("INSERT INTO hygiene_config (item, desired_interval_days) VALUES (?,?)", (item, days))
            conn.commit()
            print("Added.")
        elif choice == 'e':
            if not items:
                continue
            item_name = input("Item name to edit: ").strip()
            cur.execute("SELECT id FROM hygiene_config WHERE item=?", (item_name,))
            if not cur.fetchone():
                print("Not found.")
                continue
            try:
                days = int(input("New interval (days): "))
            except ValueError:
                print("Invalid.")
                continue
            cur.execute("UPDATE hygiene_config SET desired_interval_days=? WHERE item=?", (days, item_name))
            conn.commit()
            print("Updated.")
        elif choice == 'd':
            item_name = input("Item name to delete: ").strip()
            cur.execute("DELETE FROM hygiene_config WHERE item=?", (item_name,))
            conn.commit()
            print("Deleted.")
    conn.close()
