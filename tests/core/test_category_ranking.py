"""Tests for category suggestion ranking (TF-IDF + relative exact boost)."""

from __future__ import annotations

import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.core.journal.keywords import (
    find_matching_categories,
    learn_keywords,
    path_segments,
)


def _add_category(path: str) -> None:
    with get_connection_cm() as conn:
        conn.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (path,))
        conn.commit()


def _train(path: str, text: str, times: int = 1) -> None:
    _add_category(path)
    with get_connection_cm() as conn:
        for _ in range(times):
            learn_keywords(text, [path], conn=conn)
        conn.commit()


class TestPathSegments:
    def test_splits_on_slash_and_stems(self):
        segs = path_segments("work/coding")
        assert "work" in segs
        # "coding" stems to "code"
        assert "code" in segs

    def test_short_segments_dropped(self):
        assert path_segments("a/to") == set()

    def test_non_alpha_split(self):
        segs = path_segments("health-care/first_aid")
        assert "health" in segs
        assert "care" in segs
        assert "aid" in segs


class TestExactMatchNoFalsePositives:
    def test_substring_no_longer_matches(self, db_path):
        # "art" must not match "start"; only the real "art" category should.
        _add_category("start/routine")
        _add_category("art/painting")
        results = dict(find_matching_categories("art"))
        assert "art/painting" in results
        assert "start/routine" not in results

    def test_log_does_not_match_blog(self, db_path):
        _add_category("blog/writing")
        _add_category("log/system")
        results = dict(find_matching_categories("log"))
        assert "log/system" in results
        assert "blog/writing" not in results


class TestExactBoostIsNoticeable:
    def test_exact_match_beats_untrained_categories(self, db_path):
        _train("work/email", "responded to emails", times=1)
        _add_category("gardening/watering")
        results = find_matching_categories("gardening today")
        assert results, "expected at least one suggestion"
        assert results[0][0] == "gardening/watering"

    def test_exact_match_competes_with_heavily_trained(self, db_path):
        # Heavily train an unrelated category so its TF-IDF mass is large.
        _train("work/coding", "coding project work", times=40)
        _add_category("cooking/dinner")
        # A query that exact-matches "cooking" should surface high even though
        # "cooking" has zero training and "coding" is heavily trained.
        results = find_matching_categories("cooking dinner tonight")
        paths = [p for p, _ in results]
        assert "cooking/dinner" in paths
        # It should land in the top few, not buried at the bottom.
        assert paths.index("cooking/dinner") <= 2

    def test_multiple_segment_overlap_scores_higher(self, db_path):
        _add_category("work/coding")
        _add_category("work/email")
        results = dict(find_matching_categories("work coding session"))
        # Both share "work"; the first also matches "coding" -> higher.
        assert results["work/coding"] > results["work/email"]


class TestBasics:
    def test_empty_db_returns_empty(self, db_path):
        assert find_matching_categories("anything") == []

    def test_no_tokens_returns_empty(self, db_path):
        _add_category("work/coding")
        assert find_matching_categories("12:00") == []

    def test_results_capped_and_ordered(self, db_path):
        for i in range(15):
            _add_category(f"cat{i}/topic")
        results = find_matching_categories("topic")
        assert len(results) <= 10
        scores = [s for _, s in results]
        assert scores == sorted(scores, reverse=True)


class TestFullVsPartialMatch:
    def test_full_path_match_outranks_deeper_partial_match(self, db_path):
        # A frequently used parent category should outrank a rare child that
        # only partially matches, when the query matches the parent fully.
        _train("free_learning", "read about learning and study", times=10)
        _train("free_learning/art", "art drawing", times=1)
        results = find_matching_categories("learning study")
        paths = [p for p, _ in results]
        assert paths.index("free_learning") < paths.index("free_learning/art")

    def test_full_coverage_beats_partial_for_same_query(self, db_path):
        # Two untrained categories: the one the query fully covers wins.
        _add_category("art")
        _add_category("art/painting")
        results = dict(find_matching_categories("art"))
        assert results["art"] > results["art/painting"]

    def test_boost_does_not_overpower_strong_tfidf(self, db_path):
        # With a realistic catalog (so IDF is meaningful), a heavily trained
        # category dominated by TF-IDF must clearly outrank a category that only
        # earns the exact-match boost.
        for i in range(15):
            _add_category(f"filler{i}/topic")
        _train("work/coding", "coding project sprint", times=20)
        _add_category("coding")  # untrained; only earns the boost from "coding"
        results = dict(find_matching_categories("coding sprint"))
        assert results["work/coding"] > results["coding"]
