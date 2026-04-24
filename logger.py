import time
from datetime import datetime
from database import get_connection
from parser import extract_time

def tokenize(text: str):
    """Return lowercased list of words (simple split)."""
    return text.lower().split()

def find_matching_categories(text: str):
    """Return list of (category_path, match_count) sorted by count desc."""
    conn = get_connection()
    cur = conn.cursor()
    words = tokenize(text)
    # crude partial match: if keyword appears anywhere in any word (or whole text)
    results = {}
    for word in words:
        # search keywords that partially match
        cur.execute(
            "SELECT c.path FROM keywords k JOIN categories c ON k.category_id=c.id WHERE INSTR(?, k.word)>0",
            (word,)
        )
        for row in cur.fetchall():
            path = row['path']
            results[path] = results.get(path, 0) + 1

    conn.close()
    sorted_cats = sorted(results.items(), key=lambda x: x[1], reverse=True)[:3]
    return sorted_cats

def suggest_flags(category_path: str, text: str):
    """Return list of flag tokens that appear in text and are scoped to this category or global."""
    conn = get_connection()
    cur = conn.cursor()
    # get category ID
    cur.execute("SELECT id FROM categories WHERE path=?", (category_path,))
    cat_row = cur.fetchone()
    if not cat_row:
        conn.close()
        return []
    cat_id = cat_row[0]

    # flags where scope is this category or global
    cur.execute("SELECT token, label FROM flags WHERE scope_category_id=? OR scope_category_id IS NULL", (cat_id,))
    flags = cur.fetchall()
    conn.close()

    text_lower = text.lower()
    flagged = []
    for f in flags:
        if f['token'] in text_lower.split():  # exact token match (not partial, to avoid false)
            flagged.append(f['token'])
    return flagged

def log_free_text(cmd: str):
    """Handle a free-text entry (single line or multi-line already assembled)."""
    conn = get_connection()
    cur = conn.cursor()

    # extract time
    started_at, duration = extract_time(cmd)
    if started_at is None:
        started_at = int(time.time())
    now_ts = int(time.time())

    # find categories
    matches = find_matching_categories(cmd)
    if matches:
        print("\nSuggested categories:")
        for i, (path, cnt) in enumerate(matches, 1):
            print(f"  [{i}] {path} (matches: {cnt})")
        print("  [Enter] first  [e] edit  [space-separated numbers for multiple]")
        choice = input("> ").strip().lower()
        selected_paths = []
        if choice == '':
            selected_paths = [matches[0][0]]
        elif choice == 'e':
            custom = input("Enter category path (e.g., hygiene/shower): ").strip()
            if custom:
                # insert new category if not exists
                cur.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (custom,))
                conn.commit()
                selected_paths = [custom]
        else:
            nums = choice.split()
            for num in nums:
                try:
                    idx = int(num) - 1
                    if 0 <= idx < len(matches):
                        selected_paths.append(matches[idx][0])
                except:
                    pass

        # save entry_categories
        cur.execute("INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
                    (now_ts, started_at, duration, cmd))
        entry_id = cur.lastrowid
        for path in selected_paths:
            cur.execute("SELECT id FROM categories WHERE path=?", (path,))
            row = cur.fetchone()
            if row:
                cur.execute("INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)",
                            (entry_id, row['id']))

        # flag suggestion for each selected category
        all_flags = []
        for path in selected_paths:
            all_flags.extend(suggest_flags(path, cmd))
        all_flags = list(set(all_flags))  # unique

        if all_flags:
            print(f"\nFlags found: {', '.join(all_flags)}")
            print("  [Enter] attach all  [space-separated letters] toggle  [e] edit")
            flag_choice = input("> ").strip().lower()
            to_attach = []
            if flag_choice == '':
                to_attach = all_flags
            elif flag_choice == 'e':
                custom_flags = input("Enter flags (comma-separated): ").strip()
                if custom_flags:
                    to_attach = [f.strip() for f in custom_flags.split(',')]
            else:
                # toggle from list
                to_attach = flag_choice.split()  # naive: just attach what they typed
            for token in to_attach:
                # get flag id
                cur.execute("SELECT id FROM flags WHERE token=?", (token,))
                row = cur.fetchone()
                if row:
                    cur.execute("INSERT INTO entry_flags (entry_id, flag_id) VALUES (?,?)",
                                (entry_id, row['id']))
                else:
                    # create new flag on the fly (global)
                    cur.execute("INSERT INTO flags (token, label, scope_category_id) VALUES (?,?,NULL)",
                                (token, token))
                    cur.execute("INSERT INTO entry_flags (entry_id, flag_id) VALUES (?,?)",
                                (entry_id, cur.lastrowid))
        conn.commit()
        print("Entry logged.")
    else:
        # no category matches – prompt manual category
        cat_choice = input("No category suggestions. Enter category path (or Enter to skip): ").strip()
        if cat_choice:
            cur.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (cat_choice,))
            conn.commit()
            cur.execute("INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
                        (now_ts, started_at, duration, cmd))
            entry_id = cur.lastrowid
            cur.execute("SELECT id FROM categories WHERE path=?", (cat_choice,))
            cat_id = cur.fetchone()['id']
            cur.execute("INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)", (entry_id, cat_id))
            conn.commit()
            print("Entry logged.")
        else:
            # log with no category
            cur.execute("INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
                        (now_ts, started_at, duration, cmd))
            conn.commit()
            print("Entry logged (no category).")
    conn.close()
