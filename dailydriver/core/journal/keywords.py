"""TF-IDF based category suggestion with exact path-match boost."""

from __future__ import annotations

import math
import os
import re

from porter2stemmer import Porter2Stemmer

from dailydriver.core.database import get_connection, get_connection_cm

_stemmer = Porter2Stemmer()
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
STOPWORDS_PATH = os.path.join(PROJECT_ROOT, "data", "stopwords.txt")

# --- Exact path-match boost -------------------------------------------------
# A category whose *path* contains a query word (matched on whole segments,
# not substrings) is almost always the right bucket, yet a raw constant is
# easily buried by a heavily trained category's accumulated TF-IDF mass. So the
# boost is *relative* to the strongest TF-IDF score in this query: an exact
# match reliably lands near the top (typically #1-#3) on any database, without
# hard-pinning it to #1. ``EXACT_MATCH_FLOOR`` keeps the boost meaningful when
# TF-IDF scores are tiny or absent (e.g. a fresh database).
EXACT_MATCH_RELATIVE = 0.6
EXACT_MATCH_FLOOR = 2.0
MIN_SCORE = 0.1
MAX_RESULTS = 10


def load_stopwords() -> set[str]:
    """Load stop words from ``data/stopwords.txt``."""
    try:
        with open(STOPWORDS_PATH, encoding="utf-8") as handle:
            return {word.lower() for raw_line in handle if (word := raw_line.strip()) and not word.startswith("#")}
    except FileNotFoundError:
        return {"the", "and", "for", "not", "you", "but", "are"}


STOP_WORDS = load_stopwords()


def tokenize(text: str, stem_words: bool = True) -> list[str]:
    """Normalize *text* into deduplicated alphabetic tokens."""
    if not text:
        return []
    cleaned = re.sub(r"[^a-zA-Z]", " ", text.lower())
    unique: list[str] = []
    seen: set[str] = set()
    for token in cleaned.split():
        if len(token) < 3 or token in STOP_WORDS:
            continue
        if stem_words:
            try:
                token = _stemmer.stem(token)
            except Exception:
                pass
        if token not in seen:
            seen.add(token)
            unique.append(token)
    return unique


def path_segments(path: str) -> set[str]:
    """Split a category *path* into its comparable word segments.

    Paths are split on ``/`` and any non-alphabetic character, then each segment
    is lowered and stemmed the same way query tokens are. This lets exact-match
    detection compare whole words ("art" vs "start") instead of naive
    substrings, eliminating false positives like "art" in "start" or "log" in
    "blog".
    """
    if not path:
        return set()
    segments: set[str] = set()
    for raw in re.split(r"[^a-zA-Z]+", path.lower()):
        if len(raw) < 3:
            continue
        try:
            segments.add(_stemmer.stem(raw))
        except Exception:
            segments.add(raw)
    return segments


def find_matching_categories(text: str) -> list[tuple[str, float]]:
    """Return up to ``MAX_RESULTS`` categories scored by TF-IDF plus path boosts.

    Scoring has two stages. First, TF-IDF accumulates evidence from learned
    keywords. Then any category whose path *segments* contain a query token
    receives a boost scaled to the strongest TF-IDF score in this query, so an
    exact match surfaces near the top regardless of how well other categories
    are trained. Results are returned already ordered for direct display.
    """
    tokens = tokenize(text)
    if not tokens:
        return []
    token_set = set(tokens)

    with get_connection_cm() as conn:
        cur = conn.cursor()
        total_cats = cur.execute("SELECT COUNT(*) FROM categories").fetchone()[0]
        if total_cats == 0:
            return []

        all_cats = {row["id"]: row["path"] for row in cur.execute("SELECT id, path FROM categories")}
        scores: dict[int, float] = {}

        # --- Stage 1: TF-IDF over learned keywords ---
        for token in tokens:
            rows = cur.execute(
                """
                SELECT k.category_id, k.count,
                       (SELECT COUNT(DISTINCT k2.category_id) FROM keywords k2 WHERE k2.word = k.word) AS df
                FROM keywords k
                WHERE k.word = ?
                """,
                (token,),
            ).fetchall()
            for row in rows:
                cat_id = row["category_id"]
                tf = row["count"]
                df = row["df"]
                # Clamp IDF at 0: a word present in most categories carries no
                # discriminating signal and must never subtract from a score.
                idf = max(0.0, math.log(total_cats / (df + 1)))
                scores[cat_id] = scores.get(cat_id, 0.0) + tf * idf

        # --- Stage 2: relative exact-segment boost ---
        top_tfidf = max(scores.values(), default=0.0)
        boost = max(EXACT_MATCH_FLOOR, EXACT_MATCH_RELATIVE * top_tfidf)
        for cat_id, path in all_cats.items():
            overlap = len(path_segments(path) & token_set)
            if overlap:
                scores[cat_id] = scores.get(cat_id, 0.0) + boost * overlap

        results: list[tuple[str, float]] = []
        for cat_id, score in sorted(scores.items(), key=lambda item: item[1], reverse=True):
            if score < MIN_SCORE or len(results) >= MAX_RESULTS:
                break
            results.append((all_cats[cat_id], score))
        return results


def learn_keywords(text: str, category_paths: list[str], conn=None) -> None:
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
        row = cur.execute("SELECT id FROM categories WHERE path=?", (path,)).fetchone()
        if not row:
            continue
        cat_id = row["id"]
        for word in words:
            existing = cur.execute("SELECT id FROM keywords WHERE word=? AND category_id=?", (word, cat_id)).fetchone()
            if existing:
                cur.execute("UPDATE keywords SET count = count + 1 WHERE id=?", (existing["id"],))
            else:
                cur.execute(
                    "INSERT INTO keywords (word, category_id, count) VALUES (?, ?, 1)",
                    (word, cat_id),
                )

    if own_conn:
        conn.commit()
        conn.close()
