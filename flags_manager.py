from database import get_connection

def manage_flags():
    conn = get_connection()
    cur = conn.cursor()

    while True:
        # clear screen (we are inside REPL, but we'll just print)
        print("\n─── Flags ───")
        cur.execute('''
            SELECT f.id, f.token, f.label, f.scope_category_id,
                   COALESCE(c.path, 'global') AS scope
            FROM flags f
            LEFT JOIN categories c ON f.scope_category_id = c.id
            ORDER BY f.token
        ''')
        flags = cur.fetchall()
        if not flags:
            print("No flags defined yet.")
        else:
            for row in flags:
                print(f"  {row['token']:10} {row['label'] or '':10}  scope: {row['scope']}")

        print("\n(a)dd  (e)dit  (d)elete  (q)uit")
        choice = input("> ").strip().lower()

        if choice == 'q':
            break
        elif choice == 'a':
            token = input("Token (e.g., m, late): ").strip()
            if not token:
                continue
            label = input("Label (Enter=skip): ").strip() or None
            scope_path = input("Scope category path (Enter=global): ").strip()
            scope_id = None
            if scope_path:
                cur.execute("SELECT id FROM categories WHERE path=?", (scope_path,))
                row = cur.fetchone()
                if row:
                    scope_id = row['id']
                else:
                    print("Category not found. Using global.")
            cur.execute("INSERT INTO flags (token, label, scope_category_id) VALUES (?,?,?)",
                        (token, label, scope_id))
            conn.commit()
            print("Flag added.")
        elif choice == 'e':
            token = input("Token to edit: ").strip()
            cur.execute("SELECT id, label, scope_category_id FROM flags WHERE token=?", (token,))
            row = cur.fetchone()
            if not row:
                print("Flag not found.")
                continue
            new_label = input(f"New label (Enter=keep '{row['label']}'): ").strip()
            if new_label == '':
                new_label = row['label']
            new_scope = input("New scope category path (Enter=keep, 'global' for global): ").strip()
            if new_scope == '':
                new_scope_id = row['scope_category_id']
            elif new_scope.lower() == 'global':
                new_scope_id = None
            else:
                cur.execute("SELECT id FROM categories WHERE path=?", (new_scope,))
                r = cur.fetchone()
                if r:
                    new_scope_id = r['id']
                else:
                    print("Category not found. Keeping old scope.")
                    new_scope_id = row['scope_category_id']
            cur.execute("UPDATE flags SET label=?, scope_category_id=? WHERE id=?",
                        (new_label, new_scope_id, row['id']))
            conn.commit()
            print("Flag updated.")
        elif choice == 'd':
            token = input("Token to delete: ").strip()
            cur.execute("SELECT id FROM flags WHERE token=?", (token,))
            if not cur.fetchone():
                print("Flag not found.")
                continue
            confirm = input(f"Delete flag '{token}'? (Enter=yes, n=no): ").strip().lower()
            if confirm == '' or confirm == 'y':
                cur.execute("DELETE FROM flags WHERE token=?", (token,))
                conn.commit()
                print("Flag deleted.")
    conn.close()
