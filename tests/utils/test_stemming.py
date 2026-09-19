"""Regression tests for the built-in Porter2-compatible stemmer."""

import pytest

from dailydriver.utils.stemming import stem


@pytest.mark.parametrize(
    ("word", "expected"),
    [
        ("cat", "cat"),
        ("cats", "cat"),
        ("cat's", "cat"),
        ("meeting", "meet"),
        ("meetings", "meet"),
        ("coding", "code"),
        ("studies", "studi"),
        ("relational", "relat"),
        ("rationalization", "ration"),
        ("running", "run"),
        ("happiness", "happi"),
        ("easily", "easili"),
        ("goodness", "good"),
    ],
)
def test_stem_matches_porter2_rules(word: str, expected: str) -> None:
    assert stem(word) == expected


def test_short_words_and_initial_apostrophes_are_safe() -> None:
    assert stem("a") == "a"
    assert stem("be") == "be"
    assert stem("'running") == "run"
