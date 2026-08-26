#!/usr/bin/env python3
"""Analyse keyword stems to identify potential stopwords.

Writes a CSV file to ./stopword_candidates.csv with:
- stem
- total occurrences in entry descriptions (global, raw count)
- number of distinct categories that contain this stem
"""

import csv
import re
import sys
from collections import Counter
from pathlib import Path

from porter2stemmer import Porter2Stemmer

# Add project root to path so we can import dailydriver
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dailydriver.core.database import get_connection_cm  # noqa: E402

STEMMER = Porter2Stemmer()
MIN_STEM_LENGTH = 3
_WORD_RE = re.compile(r"[a-zA-Z]+")


def stem_entry_text(text: str) -> list[str]:
    """Return all stems (length >= 3) from a single entry description."""
    if not text:
        return []
    stems: list[str] = []
    for token in _WORD_RE.findall(text.lower()):
        if len(token) >= MIN_STEM_LENGTH:
            stems.append(STEMMER.stem(token))
    return stems


def main() -> None:
    with get_connection_cm(auto=False) as conn:
        # 1. Total occurrences across all journal entries (raw text)
        entry_counter: Counter[str] = Counter()
        cur = conn.execute(
            "SELECT description FROM entries WHERE description IS NOT NULL AND TRIM(description) != ''"
        )
        for row in cur.fetchall():
            for stem in stem_entry_text(row["description"]):
                entry_counter[stem] += 1

        # 2. Distinct category count per stem from the keywords table
        cur = conn.execute(
            "SELECT word, COUNT(DISTINCT category_id) as cat_count FROM keywords GROUP BY word"
        )
        cat_counts: dict[str, int] = {}
        for row in cur.fetchall():
            cat_counts[row["word"]] = row["cat_count"]

        # 3. Build rows: (stem, entry_count, cat_count)
        all_stems = set(entry_counter.keys()) | set(cat_counts.keys())
        rows: list[tuple[str, int, int]] = []
        for stem in all_stems:
            rows.append((stem, entry_counter.get(stem, 0), cat_counts.get(stem, 0)))

        # Sort by entry_count descending (primary), then cat_count descending (secondary)
        rows.sort(key=lambda x: (x[1], x[2]), reverse=True)

        # 4. Write CSV
        out_path = Path.cwd() / "stopword_candidates.csv"
        with open(out_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["stem", "total_occurrences", "distinct_categories"])
            for stem, entry_count, cat_count in rows:
                writer.writerow([stem, entry_count, cat_count])

        print(f"✅ Written to {out_path}")


if __name__ == "__main__":
    main()
