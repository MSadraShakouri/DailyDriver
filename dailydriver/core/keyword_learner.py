# dailydriver/core/keyword_learner.py
"""TF‑IDF based category suggestion with exact path‑match boost."""
import re
import math
import os
from dailydriver.core.database import get_connection_cm, get_connection
from porter2stemmer import Porter2Stemmer

_stemmer = Porter2Stemmer()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

def load_stopwords():
    """Load stop words from data/stopwords.txt."""
    stopwords_path = os.path.join(PROJECT_ROOT, 'data', 'stopwords.txt')
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

EXACT_MATCH_BOOST = 5.0
MIN_SCORE = 0.1
MAX_RESULTS = 10

def tokenize(text: str, stem_words: bool = True) -> list[str]:
    """
    Clean and tokenize text.
    Returns a list of lowercased, stemmed tokens suitable for keyword matching.
    """
    if not text:
        return []
    raw_tokens = text.lower().split()
    cleaned = []
    for token in raw_tokens:
        # Split hyphenated words
        sub_tokens = token.split('-')
        for sub in sub_tokens:
            # Remove possessive 's (e.g. Sadra's -> Sadra)
            sub = re.sub(r"'s$", '', sub)
            # Remove trailing apostrophe from contractions (don't -> dont)
            sub = re.sub(r"'t$", 't', sub)
            sub = re.sub(r"'re$", 're', sub)
            sub = re.sub(r"'ve$", 've', sub)
            sub = re.sub(r"'ll$", 'll', sub)
            sub = re.sub(r"'d$", 'd', sub)
            # Strip non-alphanumeric from ends, keep internal apostrophes
            sub = re.sub(r'^[^a-z0-9]+', '', sub)
            sub = re.sub(r'[^a-z0-9]+$', '', sub)
            # Discard if too short or pure digits
            if len(sub) < 2 or sub.isdigit():
                continue
            if sub in STOP_WORDS:
                continue
            # Apply stemming
            if stem_words:
                try:
                    sub = _stemmer.stem(sub)
                except Exception:
                    pass  # If stemming fails, keep original
            cleaned.append(sub)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for t in cleaned:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return unique

def find_matching_categories(text: str):
    """Return up to MAX_RESULTS categories scored by TF‑IDF + exact path boost."""
    tokens = tokenize(text)
    if not tokens:
        return []

    with get_connection_cm() as conn:
        cur = conn.cursor()

        # total number of categories
        cur.execute("SELECT COUNT(*) FROM categories")
        total_cats = cur.fetchone()[0]
        if total_cats == 0:
            return []

        # get all category paths for exact‑match boost
        cur.execute("SELECT id, path FROM categories")
        all_cats = {row['id']: row['path'] for row in cur.fetchall()}

        # category scores: id -> score
        scores = {}

        # 1. exact path‑match boost
        for token in tokens:
            token_lower = token.lower()
            for cat_id, path in all_cats.items():
                if token_lower in path.lower():
                    scores[cat_id] = scores.get(cat_id, 0) + EXACT_MATCH_BOOST

        # 2. TF‑IDF scoring
        for token in tokens:
            cur.execute("""
                SELECT k.category_id, k.count,
                       (SELECT COUNT(DISTINCT k2.category_id) FROM keywords k2 WHERE k2.word = k.word) as df
                FROM keywords k
                WHERE k.word = ?
            """, (token,))
            rows = cur.fetchall()
            for row in rows:
                cat_id = row['category_id']
                tf = row['count']
                df = row['df']
                idf = math.log(total_cats / (df + 1))
                tfidf = tf * idf
                scores[cat_id] = scores.get(cat_id, 0) + tfidf

        # sort by score descending, filter by min score, take top MAX_RESULTS
        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        results = []
        for cat_id, score in sorted_cats:
            if score < MIN_SCORE:
                break
            if len(results) >= MAX_RESULTS:
                break
            results.append((all_cats[cat_id], score))

    return results

def learn_keywords(text, category_paths, conn=None):
    """Store or increment keyword counts for selected categories."""
    if not text or not category_paths:
        return
    words = tokenize(text, stem_words=True)
    if not words:
        return

    own_conn = False
    if conn is None:
        conn = get_connection()
        own_conn = True
    cur = conn.cursor()

    for path in category_paths:
        cur.execute("SELECT id FROM categories WHERE path=?", (path,))
        row = cur.fetchone()
        if not row:
            continue
        cat_id = row['id']
        for word in words:
            cur.execute("SELECT id FROM keywords WHERE word=? AND category_id=?", (word, cat_id))
            existing = cur.fetchone()
            if existing:
                cur.execute("UPDATE keywords SET count = count + 1 WHERE id=?", (existing['id'],))
            else:
                cur.execute("INSERT INTO keywords (word, category_id, count) VALUES (?, ?, 1)", (word, cat_id))
    if own_conn:
        conn.commit()
        conn.close()
