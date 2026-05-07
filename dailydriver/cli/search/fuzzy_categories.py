# dailydriver/cli/search/fuzzy_categories.py
"""Category path boosting with optional synonym map."""
import re
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
    For each token:
      - +5.0 if the token (or a synonym) exactly matches a whole word in the category path.
      - +1.0 if it's only a substring of a word (but not an exact match).
    Only the best boost per token is kept.
    """
    if not entry_categories or entry_categories == '(no category)':
        return 0.0
    cats = entry_categories.lower().split(", ")
    score = 0.0
    for token in query_tokens:
        best_boost = 0.0
        for expanded in _expand_synonyms(token):
            expanded_lower = expanded.lower()
            # Stop checking if we already have the maximum possible boost for this token
            if best_boost == 5.0:
                break
            for cat in cats:
                # Split the category path into individual words
                words = re.split(r'[/_\-]', cat)
                for word in words:
                    if expanded_lower == word:
                        best_boost = 5.0
                        break   # stop looking at other words
                    elif expanded_lower in word:
                        # substring boost, but only if we haven't got a better match yet
                        best_boost = max(best_boost, 1.0)
                if best_boost == 5.0:
                    break   # stop looking at other categories
        score += best_boost
    return score
