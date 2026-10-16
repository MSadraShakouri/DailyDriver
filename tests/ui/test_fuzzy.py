"""Tests for the fzf-compatible matcher behind tab completion."""

import random
import shutil
import subprocess

import pytest

from dailydriver.ui.fuzzy import parse_term, rank_matches

# ── Membership: any in-order subsequence, no gap limit ──────────────────


@pytest.mark.parametrize("query", ["alex", "alemor", "amorg", "rel/ale", "relale", "morgan", "ALEX"])
def test_finds_relative_path(query):
    assert rank_matches(["work/code", "relatives/alex_morgan"], query) == ["relatives/alex_morgan"]


@pytest.mark.parametrize("query", ["zzz", "alexx", "morale", "xyz", "rss"])
def test_rejects_non_subsequences(query):
    assert rank_matches(["work/code", "relatives/alex_morgan"], query) == []


def test_initialisms_across_separators_match():
    # The old matcher capped how far apart letters could be and lost these.
    assert rank_matches(["relatives/sam_sutherland", "work/code"], "rss") == ["relatives/sam_sutherland"]


def test_no_gap_limit():
    assert rank_matches(["a" + "_" * 40 + "b" + "_" * 40 + "c"], "abc") == ["a" + "_" * 40 + "b" + "_" * 40 + "c"]


def test_query_longer_than_candidate_never_matches():
    assert rank_matches(["ab"], "abc") == []


def test_matching_is_always_case_insensitive():
    # fzf's smart-case turns case-sensitive on an uppercase letter; we do not,
    # which keeps this a superset of what fzf accepts afterwards.
    assert rank_matches(["relatives/alex_morgan"], "REL") == ["relatives/alex_morgan"]
    assert rank_matches(["FooBar"], "fb") == ["FooBar"]


def test_accents_fold_only_for_plain_ascii_queries():
    assert rank_matches(["Café", "cafe"], "cafe") == ["Café", "cafe"]  # same score and length: incoming order
    assert rank_matches(["cafe", "Café"], "cafe") == ["cafe", "Café"]
    assert rank_matches(["Café", "cafe"], "café") == ["Café"]


# ── Ordering: score, then shorter, then incoming order ──────────────────
# Expected orders below were checked against fzf 0.74.5 (``fzf -f``); the
# first four are the examples from the comment at the top of fzf's algo.go.


@pytest.mark.parametrize(
    ("query", "candidates", "expected"),
    [
        (
            "ff",
            ["fuzzyfinder", "fuzzy-finder", "fuzzy-blurry-finder"],
            ["fuzzy-finder", "fuzzyfinder", "fuzzy-blurry-finder"],
        ),
        ("br", ["foob-r", "fo-bar"], ["fo-bar", "foob-r"]),
        ("foob", ["foo-bar", "foobar"], ["foobar", "foo-bar"]),
        ("oob", ["foobar", "out-of-bound"], ["out-of-bound", "foobar"]),
        (
            "code",
            ["misc/bcode", "work/code", "codec", "c_o_d_e_x", "other"],
            ["codec", "work/code", "c_o_d_e_x", "misc/bcode"],
        ),
    ],
)
def test_ordering_matches_fzf(query, candidates, expected):
    assert rank_matches(candidates, query) == expected


def test_ties_prefer_shorter_then_incoming_order():
    assert rank_matches(["work/x1", "work/x", "aaa/x"], "x") == ["aaa/x", "work/x", "work/x1"]
    assert rank_matches(["b/x", "a/x"], "x") == ["b/x", "a/x"]


def test_index_tiebreak_keeps_incoming_order_for_equal_scores():
    paths = ["a/three", "a/one", "a/two"]
    assert rank_matches(paths, "a", tiebreak="index") == paths
    assert rank_matches(paths, "a") == ["a/one", "a/two", "a/three"]
    # A better score still wins over position.
    assert rank_matches(["xa/b", "a/b"], "a", tiebreak="index") == ["a/b", "xa/b"]


def test_duplicates_dropped_and_empty_word_keeps_order():
    assert rank_matches(["b/x", "a/x", "b/x"], "x") == ["b/x", "a/x"]
    assert rank_matches(["b", "a", "b"], "") == ["b", "a"]


# ── Operators inside a single word ───────────────────────────────────────

PATHS = ["work/code", "work/email", "relatives/alex_morgan", "code_review", "decode"]


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("'code", ["code_review", "work/code", "decode"]),
        ("'code'", ["work/code", "code_review"]),
        ("^work", ["work/code", "work/email"]),
        ("code$", ["work/code", "decode"]),
        ("^decode$", ["decode"]),
        ("!work", ["relatives/alex_morgan", "code_review", "decode"]),
        ("!^work", ["relatives/alex_morgan", "code_review", "decode"]),
        ("!code$", ["work/email", "relatives/alex_morgan", "code_review"]),
        ("!'xo", ["work/code", "work/email", "code_review", "decode"]),
    ],
)
def test_operators(query, expected):
    assert rank_matches(PATHS, query) == expected


@pytest.mark.parametrize("word", ["", "!", "'", "^", "!^", "!'"])
def test_operator_only_words_match_everything(word):
    assert parse_term(word) is None
    assert rank_matches(PATHS, word) == PATHS


def test_exclusion_only_query_is_not_sorted():
    # Same as fzf: with only inverse terms there is no score to sort by.
    assert rank_matches(["zz-long-name", "b", "a"], "!q") == ["zz-long-name", "b", "a"]


# ── Conformance with the real fzf binary (skipped when it is absent) ────


def _random_corpus(rng):
    words = ["work", "code", "relatives", "alex", "morgan", "food", "lunch", "transport", "metro", "friends", "sleep"]
    words += [
        "nap",
        "study",
        "math",
        "Quran",
        "pages",
        "FooBar",
        "foo-bar",
        "out-of-bound",
        "Café",
        "über",
        "a1b2",
        "v2",
    ]
    candidates = []
    for _ in range(rng.randint(8, 30)):
        if rng.random() < 0.8:
            joiner = rng.choice(["/", "_", "-"])
            candidates.append(joiner.join(rng.choice(words) for _ in range(rng.randint(1, 4))))
        else:
            candidates.append("".join(rng.choice("abcdefgh/_-.01AB ") for _ in range(rng.randint(1, 18))))
    return [c for c in dict.fromkeys(candidates) if c.strip()]


def _random_queries(rng, candidates):
    queries = []
    for _ in range(6):
        base = rng.choice(candidates).lower()
        kind = rng.random()
        if kind < 0.5 and len(base) >= 2:
            picks = sorted(rng.sample(range(len(base)), rng.randint(1, min(6, len(base)))))
            query = "".join(base[i] for i in picks)
        elif kind < 0.7:
            start = rng.randrange(len(base))
            query = base[start : start + rng.randint(1, 5)]
        else:
            query = "".join(rng.choice("abcdefgxyzo/_") for _ in range(rng.randint(1, 4)))
        query = "".join(ch for ch in query if ch not in " '^!$|") or "a"
        queries.append(query)
        queries.append(rng.choice(["'%s", "'%s'", "^%s", "%s$", "^%s$", "!%s", "!^%s", "!%s$", "!'%s"]) % query)
    return queries


@pytest.mark.skipif(shutil.which("fzf") is None, reason="fzf is not installed")
def test_matches_real_fzf_exactly():
    rng = random.Random(20261016)
    checked = 0
    for _ in range(25):
        candidates = _random_corpus(rng)
        for query in _random_queries(rng, candidates):
            for tiebreak in ("length", "index"):
                expected = subprocess.run(
                    ["fzf", "-f", query, f"--tiebreak={tiebreak}"],
                    input="\n".join(candidates) + "\n",
                    capture_output=True,
                    text=True,
                    check=False,
                ).stdout.split("\n")[:-1]
                assert rank_matches(candidates, query, tiebreak=tiebreak) == expected, (query, tiebreak, candidates)
                checked += 1
    assert checked > 400
