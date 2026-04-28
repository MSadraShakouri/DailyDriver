# dailydriver/core/keyword_learner.py
import re
import time
import os
from dailydriver.core.database import get_connection_cm, get_connection

# Project root for stopwords.txt
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

def load_stopwords():
    """Load stop words from stopwords.txt."""
    stopwords_path = os.path.join(PROJECT_ROOT, 'stopwords.txt')
    stop_set = set()
    try:
        with open(stopwords_path, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip()
                if word and not word.startswith('#'):
                    stop_set.add(word.lower())
    except FileNotFoundError:
        stop_set = {'the', 'and', 'for', 'not', 'you', 'but', 'are'}
    return stop_set

STOP_WORDS = load_stopwords()

def tokenize(text: str):
    """Return lowercased list of words (simple split)."""
    return text.lower().split()

def find_matching_categories(text: str):
    """Return list of (category_path, match_count) sorted by count desc."""
    with get_connection_cm() as conn:
        cur = conn.cursor()
        words = tokenize(text)
        results = {}
        for word in words:
            cur.execute(
                "SELECT c.path FROM keywords k JOIN categories c ON k.category_id=c.id WHERE INSTR(?, k.word)>0",
                (word,)
            )
            for row in cur.fetchall():
                path = row['path']
                results[path] = results.get(path, 0) + 1
    sorted_cats = sorted(results.items(), key=lambda x: x[1], reverse=True)[:3]
    return sorted_cats

def learn_keywords(text, category_paths, conn=None):
    if not text or not category_paths:
        return
    words = tokenize(text)
    cleaned = []
    for w in words:
        w = re.sub(r'^[^a-zA-Z]+|[^a-zA-Z]+$', '', w)
        if w in STOP_WORDS:
            continue
        if len(w) < 3:
            continue
        if not re.fullmatch(r'[a-zA-Z-]+', w):
            continue
        cleaned.append(w)
    if not cleaned:
        return

    own_conn = False
    if conn is None:
        conn = get_connection()
        own_conn = True
    cur = conn.cursor()
    now_ts = int(time.time())

    for path in category_paths:
        cur.execute("SELECT id FROM categories WHERE path=?", (path,))
        row = cur.fetchone()
        if not row:
            continue
        cat_id = row['id']
        for word in cleaned:
            cur.execute("SELECT id FROM keywords WHERE word=? AND category_id=?", (word, cat_id))
            if cur.fetchone():
                continue
            cur.execute("SELECT id FROM pending_keywords WHERE word=? AND category_id=?", (word, cat_id))
            if cur.fetchone():
                cur.execute("DELETE FROM pending_keywords WHERE word=? AND category_id=?", (word, cat_id))
                cur.execute("INSERT INTO keywords (word, category_id) VALUES (?,?)", (word, cat_id))
                continue
            cur.execute("INSERT OR IGNORE INTO pending_keywords (word, category_id, first_seen) VALUES (?,?,?)",
                        (word, cat_id, now_ts))
    if own_conn:
        conn.commit()
        conn.close()
