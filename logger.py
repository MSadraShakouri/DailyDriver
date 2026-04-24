import time
from datetime import datetime
from database import get_connection
from parser import extract_time
import re

STOP_WORDS = set([
    # articles, conjunctions, prepositions
    'a','an','the','and','or','but','if','in','on','at','to','for',
    'of','with','by','from','up','down','about','into','through',
    'before','after','since','until','while','during','because',
    'than','even','still','already','yet','ago',
    'due','last','day','days','week','weeks','month','months',

    # pronouns
    'i','me','my','mine','myself','we','our','ours','you','your',
    'he','him','his','she','her','it','its','they','them','this','that',
    'these','those','which','who','whom','what','whatever','whoever',

    # possessives & reflexive
    'itself','himself','herself','yourself','ourselves','themselves',

    # common verbs & auxiliaries
    'is','was','are','were','been','be','have','has','had','do',
    'does','did','can','could','will','would','shall','should',
    'may','might','must','need','dare','ought','used',
    'am','not','no','nor','just','only','very','too','so',

    # adverbs / adverbials
    'then','now','here','there','all','some','any','each','every',
    'few','more','most','other','such','own','same',
    'also','like','well','how',
    'again','further','once','twice','often','always','never',
    'ever','hardly','almost','enough','quite','rather','almost',

    # conversational filler / common journal words
    'today','yesterday','tomorrow',
    'morning','evening','night','afternoon',
    'did','done','doing',
    'come','came','coming',
    'say','said','saying',
    'think','thinking','thought',
    'know','knew','known',
    'take','took','taking',
    'make','made','making',
    'see','saw','seeing',
    'give','gave','giving',
    'find','found','finding',
    'tell','told','telling',
    'ask','asked','asking',

    # numbers (should never be keywords)
    'one','two','three','four','five','six','seven','eight','nine','ten',
    'first','second','third','last',

    # time / duration words (already in parser, not useful as keywords)
    'min','mins','minute','minutes','hour','hours','hr','hrs',

    # flag tokens (keep out of keywords)
    'm','s',

    # common words that carry no category
    'thing','things','stuff','lot','bit','part','way',
    'time','times',
    'yes','yeah','no','nope',
    'ok','okay','ah','oh','um','er',
    'really','pretty','quite','rather','maybe','perhaps',
    'also','else','anyway','though','although',
    'still','yet','already',
    'half','full','many','much','little','big','small',
    'new','old','good','bad','great','nice','fine','best',
    'worse','worst','better',
    'right','wrong','left','front','back','top','bottom',
    'high','low','short','long','hard','soft',
    'early','late',

    # standard journal connective words
    'then','next','finally','first','second','third',
    'because','since','as','so','hence','thus',
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
    # Filter: only keep tokens that are purely alphabetic (or contain hyphens),
    # at least 3 characters, and are not stop words.
    cleaned = []
    for w in words:
        # Remove leading/trailing punctuation (commas, periods, etc.)
        w = re.sub(r'^[^a-zA-Z]+|[^a-zA-Z]+$', '', w)
        if w in STOP_WORDS:
            continue
        if len(w) < 3:
            continue
        # Allow only letters and hyphens
        if not re.fullmatch(r'[a-zA-Z-]+', w):
            continue
        cleaned.append(w)

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
    import time
    from datetime import datetime

    conn = get_connection()
    cur = conn.cursor()
    selected_paths = []
    result = ""                 # will build a short summary with line breaks

    # ---------- step 0 – time extraction and confirmation ----------
    started_at, duration = extract_time(cmd)
    if started_at is not None:
        # time was found → confirm
        start_dt = datetime.fromtimestamp(started_at)
        start_str = start_dt.strftime('%H:%M')
        dur_str = ""
        if duration is not None:
            h = duration // 60
            m = duration % 60
            dur_str = f"{h}h {m}m" if h else f"{m}m"

        print()
        print(f"Time:   {start_str}")
        if dur_str:
            print(f"Duration: {dur_str}")
        print("(Enter=yes, n=cancel)")
        confirm = input("> ").strip().lower()
        if confirm == 'n':
            conn.close()
            return None
        # keep the parsed times
    else:
        # no time found – default to now
        started_at = int(time.time())

    # ---------- step 1 – category suggestion ----------
    matches = find_matching_categories(cmd)
    if matches:
        print()
        print("Suggested categories:")
        for i, (path, cnt) in enumerate(matches, 1):
            print(f"  [{i}] {path}")
        print("Enter=1, numbers to select, or type new paths (space‑separated)")
        choice = input("> ").strip().lower()
        if choice == '':
            selected_paths = [matches[0][0]]
        else:
            for token in choice.split():
                if token.isdigit():
                    # selection by number
                    try:
                        idx = int(token) - 1
                        if 0 <= idx < len(matches):
                            selected_paths.append(matches[idx][0])
                    except ValueError:
                        pass
                else:
                    # new category path – as typed, no autocorrect
                    cur.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (token,))
                    conn.commit()
                    selected_paths.append(token)
    else:
        cat_choice = input("No suggestions. Enter category path (or Enter to skip): ").strip().lower()
        if cat_choice:
            # same space‑is‑separator rule here
            for token in cat_choice.split():
                if token:
                    cur.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (token,))
                    conn.commit()
                    selected_paths.append(token)

    # ---------- step 2 – insert entry ----------
    cur.execute(
        "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
        (int(time.time()), started_at, duration, cmd)
    )
    entry_id = cur.lastrowid

    for path in selected_paths:
        cur.execute("SELECT id FROM categories WHERE path=?", (path,))
        row = cur.fetchone()
        if row:
            cur.execute("INSERT INTO entry_categories (entry_id, category_id) VALUES (?,?)",
                        (entry_id, row['id']))

    # ---------- step 3 – flags (always prompt) ----------
    print("\nFlags? (Enter=none, or type tokens)")
    flag_input = input("> ").strip().lower()
    attached_flags = []
    if flag_input:
        tokens = flag_input.split()
        for token in tokens:
            cur.execute("SELECT id FROM flags WHERE token=?", (token,))
            frow = cur.fetchone()
            if frow:
                cur.execute("INSERT INTO entry_flags (entry_id, flag_id) VALUES (?,?)",
                            (entry_id, frow['id']))
                attached_flags.append(token)
            else:
                # create new global flag on the fly
                cur.execute("INSERT INTO flags (token, label, scope_category_id) VALUES (?,?,NULL)",
                            (token, token))
                cur.execute("INSERT INTO entry_flags (entry_id, flag_id) VALUES (?,?)",
                            (entry_id, cur.lastrowid))
                attached_flags.append(token)

    conn.commit()

    # ---------- step 4 – learn keywords ----------
    learn_keywords(cmd, selected_paths)
    conn.close()

    # ---------- build result string (short lines) ----------
    if selected_paths:
        result += "Logged:\n"
        for p in selected_paths:
            result += f"  {p}\n"
    if started_at:
        start_dt = datetime.fromtimestamp(started_at)
        result += f"Time:   {start_dt.strftime('%H:%M')}\n"
    if duration is not None:
        h = duration // 60
        m = duration % 60
        result += f"Duration: {h}h {m}m\n" if h else f"Duration: {m}m\n"
    if attached_flags:
        result += f"Flags:  {', '.join(attached_flags)}\n"
    return result.strip()
