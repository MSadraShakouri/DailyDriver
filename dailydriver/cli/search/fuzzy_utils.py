# dailydriver/cli/search/fuzzy_utils.py
"""Levenshtein distance and fuzzy token matching."""

def levenshtein(s1: str, s2: str) -> int:
    """Compute edit distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]

def fuzzy_match(token: str, candidates: list[str], max_dist: int = 2) -> str | None:
    """Return the best matching candidate if within max_dist, else None."""
    token = token.lower()
    best = None
    best_dist = max_dist + 1
    for cand in candidates:
        dist = levenshtein(token, cand.lower())
        if dist < best_dist:
            best_dist = dist
            best = cand
            if dist == 0:
                break
    return best if best_dist <= max_dist else None
