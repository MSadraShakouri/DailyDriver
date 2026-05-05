# dailydriver/cli/search/fuzzy_categories.py
"""Category path boosting with optional synonym map."""
from dailydriver.core.database import get_connection_cm

# Small synonym map (manually editable)
SYNONYMS = {
    "food": ["cooking", "eating", "meal"],
    "class": ["uni", "university", "lecture"],
    "work": ["programming", "coding", "project"],
    "sleep": ["nap", "rest"],
}

def _expand_synonyms(word: str) -> list[str]:
    """Return a list of words that are synonymous with word (including the word itself)."""
    results = {word}
    word_l = word.lower()
    for key, values in SYNONYMS.items():
        if word_l == key or word_l in values:
            results.add(key)
            results.update(values)
    return list(results)

def score_categories(entry_categories: str, query_tokens: list[str]) -> float:
    """Return a category boost score.
    For each token that matches a part of the category path (exact substring),
    or one of its synonyms, add +5.0.
    """
    if not entry_categories or entry_categories == '(no category)':
        return 0.0
    cats = entry_categories.lower().split(", ")
    score = 0.0
    for token in query_tokens:
        for expanded in _expand_synonyms(token):
            for cat in cats:
                if expanded.lower() in cat:
                    score += 5.0
                    break  # only count once per token
    return score
