# dailydriver/cli/search/scoring.py
"""Merge FTS/LIKE results and compute final scores."""
from .fuzzy_time import score_time
from .fuzzy_dates import score_dates
from .fuzzy_categories import score_categories

def compute_final_scores(fts_results: list[dict], like_results: list[dict],
                         query_tokens: list[str]) -> list[dict]:
    """Merge, deduplicate, compute final scores, sort descending."""
    seen_ids = set()
    all_entries = []
    for entry in fts_results:
        if entry['id'] not in seen_ids:
            seen_ids.add(entry['id'])
            all_entries.append(entry)
    for entry in like_results:
        if entry['id'] not in seen_ids:
            seen_ids.add(entry['id'])
            all_entries.append(entry)

    for entry in all_entries:
        # FTS score: rank is negative; least negative = best.
        # Convert to a positive score in [0,1] using 1/(abs(rank)+1)
        if entry.get('relevance') is not None:
            try:
                rel = float(entry['relevance'])
                fts_score = 1.0 / (abs(rel) + 1.0)
            except (TypeError, ValueError):
                fts_score = 0.0
        else:
            fts_score = 0.0

        time_score = score_time(entry.get('started_at'), query_tokens)
        date_score = score_dates(entry.get('created_at'), query_tokens)
        cat_score = score_categories(entry.get('categories', ''), query_tokens)

        entry['final_score'] = fts_score + time_score + date_score + cat_score

    all_entries.sort(key=lambda x: (x['final_score'], x['created_at']), reverse=True)
    return all_entries
