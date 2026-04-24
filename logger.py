import time
from datetime import datetime
from database import get_connection
from parser import extract_time

# put this near the top, after imports
STOP_WORDS = set([
    'a','an','the','and','or','but','if','in','on','at','to','for',
    'of','with','by','from','up','down','about','into','through',
    'is','was','are','were','been','be','have','has','had','do',
    'does','did','i','me','my','mine','myself','we','our','ours','you','your',
    'he','him','his','she','her','it','its','they','them','this','that',
    'these','those','not','no','nor','just','only','very','too','so',
    'then','now','here','there','all','some','any','each','every',
    'few','more','most','other','such','own','same','can','will',
    'shall','would','could','should','may','might','must','need',
    'dare','ought','used','also','like','well','how',
    'than','even','still','already','yet','ago',
    'because','until','while','during','before','after','since',
    'm','s',   # flags
    'due','last','day','days','week','weeks','month','months',
])

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

def learn_keywords(text, category_paths):
    if not text or not category_paths:
        return
    words = tokenize(text)
    cleaned = [w for w in words if w not in STOP_WORDS and len(w) > 1]
    if not cleaned:
        return
    conn = get_connection()
    cur = conn.cursor()
    for path in category_paths:
        cur.execute("SELECT id FROM categories WHERE path=?", (path,))
        row = cur.fetchone()
        if not row:
            continue
        cat_id = row['id']
        for word in cleaned:
            cur.execute("SELECT id FROM keywords WHERE word=? AND category_id=?", (word, cat_id))
            if not cur.fetchone():
                cur.execute("INSERT INTO keywords (word, category_id) VALUES (?,?)", (word, cat_id))
    conn.commit()
    conn.close()

def log_free_text(cmd):
    conn = get_connection()
    cur = conn.cursor()
    selected_paths = []

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
        if choice == '':
            selected_paths = [matches[0][0]]
        elif choice == 'e':
            custom = input("Enter category path (e.g., hygiene/shower): ").strip()
            if custom:
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

        # save entry and categories
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
        all_flags = list(set(all_flags))

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
                to_attach = flag_choice.split()
            for token in to_attach:
                cur.execute("SELECT id FROM flags WHERE token=?", (token,))
                row = cur.fetchone()
                if row:
                    cur.execute("INSERT INTO entry_flags (entry_id, flag_id) VALUES (?,?)",
                                (entry_id, row['id']))
                else:
                    cur.execute("INSERT INTO flags (token, label, scope_category_id) VALUES (?,?,NULL)",
                                (token, token))
                    cur.execute("INSERT INTO entry_flags (entry_id, flag_id) VALUES (?,?)",
                                (entry_id, cur.lastrowid))

        conn.commit()
        # learn keywords from this text for the selected categories
        learn_keywords(cmd, selected_paths)
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
            selected_paths = [cat_choice]
            conn.commit()
            learn_keywords(cmd, selected_paths)
            print("Entry logged.")
        else:
            cur.execute("INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
                        (now_ts, started_at, duration, cmd))
            conn.commit()
            print("Entry logged (no category).")
    conn.close()
