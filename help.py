from database import get_connection

def show_help():
    conn = get_connection()
    cur = conn.cursor()

    print("\n─── Commands ───")
    print("P [offset/time]    S <sleep> <wake>    RQ    MP    BD    T")
    print("hygiene            stats               today view [filter]")
    print("flags              :m (multi-line)     ?     q (quit)")

    print("\n─── Categories & Top Keywords ───")
    cur.execute("SELECT path FROM categories ORDER BY path")
    cats = cur.fetchall()
    if not cats:
        print("  No categories yet.")
    else:
        for cat in cats:
            cur.execute("""
                SELECT word FROM keywords
                WHERE category_id = (SELECT id FROM categories WHERE path=?)
                ORDER BY word
                LIMIT 8
            """, (cat['path'],))
            words = [row['word'] for row in cur.fetchall()]
            word_str = ', '.join(words) if words else '(no keywords)'
            print(f"  {cat['path']}")
            print(f"    {word_str}")

    print("\n─── Flags ───")
    cur.execute('''
        SELECT f.token, f.label, COALESCE(c.path, 'global') AS scope
        FROM flags f
        LEFT JOIN categories c ON f.scope_category_id = c.id
        ORDER BY f.token
    ''')
    flags = cur.fetchall()
    if not flags:
        print("  No flags defined.")
    else:
        for f in flags:
            scope_str = f"scope: {f['scope']}"
            print(f"  {f['token']:10} {f['label'] or '':10} {scope_str}")

    conn.close()
