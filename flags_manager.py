from database import get_connection
from database import commit_and_update

def create_flag_interactive(token, default_scope_path=None, conn=None):
    """
    Prompt for label and scope, then insert the flag.
    If conn is given, use it; otherwise open our own.
    Returns the new flag id, or None if cancelled.
    """
    own_conn = False
    if conn is None:
        conn = get_connection()
        own_conn = True
    cur = conn.cursor()

    print(f"\nNew flag: '{token}'")
    label = input("Label (Enter=use token): ").strip()
    if not label:
        label = token

    if default_scope_path:
        prompt = f"Scope category path (Enter={default_scope_path}, 'global' for global): "
    else:
        prompt = "Scope category path (Enter=global): "

    scope_path = input(prompt).strip().lower()
    scope_id = None

    if scope_path == '':
        if default_scope_path:
            cur.execute("SELECT id FROM categories WHERE path=?", (default_scope_path,))
            row = cur.fetchone()
            if row:
                scope_id = row['id']
    elif scope_path == 'global':
        scope_id = None
    else:
        cur.execute("SELECT id FROM categories WHERE path=?", (scope_path,))
        row = cur.fetchone()
        if row:
            scope_id = row['id']
        else:
            print("Category not found – making global.")
            scope_id = None

    cur.execute("INSERT INTO flags (token, label, scope_category_id) VALUES (?,?,?)",
                (token, label, scope_id))
    if own_conn:
        commit_and_update(conn)
        conn.close()

    return cur.lastrowid

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
            scope_path = input("Scope category path (Enter=global): ").strip().lower()
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
            commit_and_update(conn)
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
            new_scope = input("New scope category path (Enter=keep, 'global' for global): ").strip().lower()
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
            commit_and_update(conn)
            print("Flag updated.")
        elif choice == 'd':
            token = input("Token to delete: ").strip()
            cur.execute("SELECT id FROM flags WHERE token=?", (token,))
            frow = cur.fetchone()
            if not frow:
                print("Flag not found.")
                continue
            flag_id = frow['id']
            confirm = input(f"Delete flag '{token}'? (Enter=yes, n=no): ").strip().lower()
            if confirm == '' or confirm == 'y':
                # Remove the flag from all entries first
                cur.execute("DELETE FROM entry_flags WHERE flag_id=?", (flag_id,))
                cur.execute("DELETE FROM flags WHERE id=?", (flag_id,))
                commit_and_update(conn)
                print("Flag deleted.")
    conn.close()
