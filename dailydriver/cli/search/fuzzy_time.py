# dailydriver/cli/search/fuzzy_time.py
"""Time‑of‑day scoring with wide overlapping ranges and fuzzy token matching."""

from datetime import datetime

from .fuzzy_utils import fuzzy_match

# Canonical time tokens (lowercase)
TIME_TOKENS = {
    "morning": ("morning",),
    "noon": ("noon", "midday"),
    "afternoon": ("afternoon",),
    "night": ("evening", "night"),
}

# Each label maps to (start_hour, end_hour) in 24‑h format.
# End hour can be < start to span midnight.
TIME_RANGES = {
    "morning": (2, 12),
    "noon": (9, 16),
    "afternoon": (12, 19),
    "night": (16, 4),  # 16:00 to 04:00 next day
}


def _hour_in_range(hour: float, start: int, end: int) -> float:
    """Return distance in hours from hour to the range, 0 if inside."""
    if start <= end:
        if start <= hour < end:
            return 0.0
        # distance to nearest endpoint
        return min(abs(hour - start), abs(hour - end))
    else:
        # overnight range
        if hour >= start or hour < end:
            return 0.0
        # distance to start (if before start) or to end (if after end)
        dist_to_start = (hour - start) % 24
        dist_to_end = (end - hour) % 24
        return min(dist_to_start, dist_to_end)


def score_time(entry_started_at_unix: int | None, query_tokens: list[str]) -> float:
    """Return a time‑of‑day score for an entry based on query tokens.
    Each matched time token contributes a score in [0,1] based on distance to its range.
    Multiple matches are summed.
    """
    if entry_started_at_unix is None:
        return 0.0
    entry_dt = datetime.fromtimestamp(entry_started_at_unix)
    hour = entry_dt.hour + entry_dt.minute / 60.0

    score = 0.0
    for token in query_tokens:
        matched_label = None
        # Fuzzy match against all canonical tokens
        for label, aliases in TIME_TOKENS.items():
            candidates = list(aliases)
            match = fuzzy_match(token, candidates, max_dist=2)
            if match:
                matched_label = label
                break
        if matched_label is None:
            continue
        start, end = TIME_RANGES[matched_label]
        dist_hours = _hour_in_range(hour, start, end)
        if dist_hours == 0.0:
            score += 1.0
        else:
            # Linear falloff over 6 hours
            score += max(0.0, 1.0 - dist_hours / 6.0)
    return score
