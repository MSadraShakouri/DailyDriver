"""Behaviour tests for the standalone category editor tool (tools/).

The tool is not part of the dailydriver package, so it is loaded by file
path.  The ``db_path`` fixture points DAILYDRIVER_DB at a migrated,
test-local database; the tool resolves the path per connection, so the
fixture applies to every call.
"""

import importlib.util
import os
import sqlite3

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_spec = importlib.util.spec_from_file_location(
    "category_editor", os.path.join(REPO_ROOT, "tools", "category_editor.py")
)
ce = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ce)


def _seed(conn, categories=(), entries=(), keywords=(), meta=()):
    """categories: [path]; entries: [(path, description)] using created_at
    in list order; keywords: [(path, word, count)]; meta: [(key, value)]."""
    for path in categories:
        conn.execute("INSERT INTO categories (path) VALUES (?)", (path,))
    ids = {
        path: cid for cid, path in conn.execute("SELECT id, path FROM categories").fetchall()
    }
    for path, description in entries:
        cur = conn.execute(
            "INSERT INTO entries (created_at, description) VALUES (?, ?)",
            (1000, description),
        )
        conn.execute(
            "INSERT INTO entry_categories (entry_id, category_id) VALUES (?, ?)",
            (cur.lastrowid, ids[path]),
        )
    for path, word, count in keywords:
        conn.execute(
            "INSERT INTO keywords (word, category_id, count) VALUES (?, ?, ?)",
            (word, ids[path], count),
        )
    for key, value in meta:
        conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES (?, ?)", (key, value)
        )


def _cat_id(conn, path):
    return conn.execute("SELECT id FROM categories WHERE path = ?", (path,)).fetchone()[0]


def _conn(db):
    conn = sqlite3.connect(str(db))
    conn.row_factory = sqlite3.Row
    return conn


def _row(conn, sql, *args):
    return conn.execute(sql, args).fetchone()


# ---------------------------------------------------------------------------
# path validation
# ---------------------------------------------------------------------------

def test_normalize_path_trims_and_validates():
    assert ce.normalize_path("  work/fitness ") == "work/fitness"
    for bad in ("", "   ", "/work", "work/", "work//home", "my cat", "a\nb"):
        try:
            ce.normalize_path(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"expected ValueError for {bad!r}")


def test_levenshtein_and_similarity():
    assert ce.levenshtein("kitten", "sitting") == 3
    assert ce.levenshtein("abc", "abc") == 0
    assert ce.similarity("work/fitness", "work/fitnes") > 0.9
    assert ce.similarity("work", "work/home") < 0.8


# ---------------------------------------------------------------------------
# listing
# ---------------------------------------------------------------------------

def test_get_categories_counts_and_ordering(db_path):
    conn = _conn(db_path)
    _seed(
        conn,
        categories=["alpha", "beta", "gamma", "health", "Health"],
        entries=[("beta", "b1"), ("beta", "b2"), ("alpha", "a1")],
    )
    conn.commit()
    conn.close()

    cats = ce.get_categories()
    # alphabetical, case-insensitive (case variant: "Health" before "health")
    assert [c["path"] for c in cats] == ["alpha", "beta", "gamma", "Health", "health"]
    assert [c["entry_count"] for c in cats] == [1, 2, 0, 0, 0]


def test_get_entries_limit_most_recent_and_null_description(db_path):
    conn = _conn(db_path)
    _seed(conn, categories=["alpha"], entries=[("alpha", f"e{i}") for i in range(25)])
    # NULL-description entry, also the most recent one
    cur = conn.execute(
        "INSERT INTO entries (created_at, description) VALUES (?, ?)",
        (9999, None),
    )
    conn.execute(
        "INSERT INTO entry_categories (entry_id, category_id) VALUES (?, ?)",
        (cur.lastrowid, _cat_id(conn, "alpha")),
    )
    conn.commit()
    conn.close()

    conn = _conn(db_path)
    cat_id = _cat_id(conn, "alpha")
    conn.close()
    data = ce.get_entries_for_category(cat_id)
    assert data["total"] == 26
    assert len(data["entries"]) == 20
    assert data["has_more"] is True
    assert data["entries"][0]["description"] == ""  # NULL renders as ""


# ---------------------------------------------------------------------------
# suggestions
# ---------------------------------------------------------------------------

def test_suggestions_threshold_direction_and_dedup(db_path):
    conn = _conn(db_path)
    _seed(conn, categories=["health", "Health", "dinner", "dinner2", "zzz"])
    conn.commit()
    conn.close()

    suggestions = ce.get_suggestions()
    pairs = {(s["source_path"], s["target_path"]) for s in suggestions}
    assert ("Health", "health") in pairs  # case variants, alphabetical order
    assert ("dinner", "dinner2") in pairs
    # every pair appears exactly once, never reversed
    all_paths = []
    for s in suggestions:
        all_paths.append((s["source_path"], s["target_path"]))
    assert len(all_paths) == len(set(all_paths))
    for s in suggestions:
        assert s["similarity"] >= 0.80
    assert not any("zzz" in (s["source_path"], s["target_path"]) for s in suggestions)


def test_suggestions_only_path_filter(db_path):
    conn = _conn(db_path)
    _seed(conn, categories=["health", "Health", "dinner", "dinner2", "zzz"])
    conn.commit()
    conn.close()

    # case-insensitive match, returns only pairs involving that path
    subset = ce.get_suggestions(only_path="DINNER")
    assert [(s["source_path"], s["target_path"]) for s in subset] == [("dinner", "dinner2")]
    # a path with no near-duplicates returns nothing
    assert ce.get_suggestions(only_path="zzz") == []


# ---------------------------------------------------------------------------
# rename
# ---------------------------------------------------------------------------

def test_rename_noop_and_uniqueness(db_path):
    conn = _conn(db_path)
    _seed(conn, categories=["Health", "health"])
    conn.commit()
    conn.close()

    health_id = _cat_id(_conn(db_path), "Health")
    # exact same name: no-op success even with a case sibling present
    result = ce.rename_category(health_id, "Health")
    assert result["warnings"] == []
    # case change blocked by the case-insensitive sibling
    try:
        ce.rename_category(health_id, "HEALTH")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "already exists" in str(exc)
    # real rename works
    ce.rename_category(health_id, "Wellness")
    conn = _conn(db_path)
    assert _row(conn, "SELECT path FROM categories WHERE id = ?", health_id)["path"] == "Wellness"
    conn.close()


def test_rename_syncs_great_event_meta_and_warns_on_hygiene(db_path):
    conn = _conn(db_path)
    _seed(
        conn,
        categories=["gym", "hygiene/brush"],
        meta=[("great_event_start", "123"), ("great_event_categories", "gym work")],
    )
    conn.execute("INSERT INTO hygiene_config (item, desired_interval_days) VALUES ('brush', 1)")
    conn.commit()
    conn.close()

    db = str(db_path)
    gym_id = _cat_id(_conn(db), "gym")
    ce.rename_category(gym_id, "Workout")
    conn = _conn(db)
    assert _row(conn, "SELECT value FROM meta WHERE key = 'great_event_categories'")["value"] == "Workout work"
    conn.close()

    brush_id = _cat_id(_conn(db), "hygiene/brush")
    result = ce.rename_category(brush_id, "care/brushing")
    assert any("Hygiene item 'brush'" in w for w in result["warnings"])
    # suffix still matches: no warning
    result = ce.rename_category(brush_id, "personal/brush")
    assert result["warnings"] == []


def test_rename_rejects_unknown_category(db_path):
    try:
        ce.rename_category(999, "x")
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "not found" in str(exc)


# ---------------------------------------------------------------------------
# merge
# ---------------------------------------------------------------------------

def test_merge_moves_entries_and_dedupes(db_path):
    db = str(db_path)
    conn = _conn(db)
    _seed(
        conn,
        categories=["src", "tgt"],
        entries=[("src", "only src"), ("tgt", "only tgt")],
    )
    # one entry tagged with BOTH
    cur = conn.execute("INSERT INTO entries (created_at, description) VALUES (?, 'both')", (2000,))
    both = cur.lastrowid
    conn.execute("INSERT INTO entry_categories VALUES (?, ?)", (both, _cat_id(conn, "src")))
    conn.execute("INSERT INTO entry_categories VALUES (?, ?)", (both, _cat_id(conn, "tgt")))
    conn.commit()
    conn.close()

    ce.merge_categories(_cat_id(_conn(db), "src"), _cat_id(_conn(db), "tgt"), "tgt")

    conn = _conn(db)
    assert _row(conn, "SELECT COUNT(*) AS n FROM categories WHERE path = 'src'")["n"] == 0
    assert _row(conn, "SELECT COUNT(*) AS n FROM entry_categories WHERE category_id = ?", _cat_id(conn, "tgt"))["n"] == 3
    assert _row(conn, "SELECT COUNT(*) AS n FROM entry_categories WHERE entry_id = ?", both)["n"] == 1
    conn.close()


def test_merge_sums_keywords_including_duplicate_target_rows(db_path):
    db = str(db_path)
    conn = _conn(db)
    _seed(
        conn,
        categories=["src", "tgt"],
        keywords=[("tgt", "meal", 2), ("tgt", "meal", 5), ("tgt", "rice", 1), ("src", "meal", 3), ("src", "soup", 1)],
    )
    conn.commit()
    conn.close()

    ce.merge_categories(_cat_id(_conn(db), "src"), _cat_id(_conn(db), "tgt"), "tgt")

    conn = _conn(db)
    counts = {
        r["word"]: r["total"]
        for r in conn.execute(
            "SELECT word, SUM(count) AS total FROM keywords WHERE category_id = ?"
            " GROUP BY word",
            (_cat_id(conn, "tgt"),),
        )
    }
    # source 'meal' (3) added to exactly one target row: 2+3 or 5+3 -> total 10
    assert counts == {"meal": 10, "rice": 1, "soup": 1}
    assert _row(conn, "SELECT COUNT(*) AS n FROM keywords WHERE category_id = ?", _cat_id(conn, "tgt"))["n"] == 4
    conn.close()


def test_merge_can_take_source_name(db_path):
    db = str(db_path)
    conn = _conn(db)
    _seed(conn, categories=["old/name", "other"])
    conn.commit()
    conn.close()

    ce.merge_categories(
        _cat_id(_conn(db), "old/name"),
        _cat_id(_conn(db), "other"),
        "old/name",  # result keeps the source's path (source excluded from check)
    )
    conn = _conn(db)
    assert _row(conn, "SELECT COUNT(*) AS n FROM categories")["n"] == 1
    assert _row(conn, "SELECT path FROM categories")["path"] == "old/name"
    conn.close()


def test_merge_rejections_and_rollback(db_path):
    db = str(db_path)
    conn = _conn(db)
    _seed(conn, categories=["a", "b", "c"], keywords=[("a", "word", 1)])
    conn.commit()
    conn.close()

    a = _cat_id(_conn(db), "a")
    b = _cat_id(_conn(db), "b")
    for args in ((a, a, "a"), (a, b, "c"), (a, 999, "x")):
        try:
            ce.merge_categories(*args)
            assert False, f"expected ValueError for {args}"
        except ValueError:
            pass
    # nothing changed
    conn = _conn(db)
    assert _row(conn, "SELECT COUNT(*) AS n FROM categories")["n"] == 3
    assert _row(conn, "SELECT COUNT(*) AS n FROM keywords")["n"] == 1
    conn.close()


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------

def test_delete_rejects_categories_with_entries(db_path):
    db = str(db_path)
    conn = _conn(db)
    _seed(conn, categories=["used"], entries=[("used", "e1")])
    conn.commit()
    conn.close()

    try:
        ce.delete_category(_cat_id(_conn(db), "used"))
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "referenced by 1 entry" in str(exc)


def test_delete_removes_empty_category_keywords_and_meta(db_path):
    db = str(db_path)
    conn = _conn(db)
    _seed(
        conn,
        categories=["unused"],
        keywords=[("unused", "ghost", 2)],
        meta=[("great_event_start", "1"), ("great_event_categories", "unused other")],
    )
    conn.commit()
    conn.close()

    ce.delete_category(_cat_id(_conn(db), "unused"))
    conn = _conn(db)
    assert _row(conn, "SELECT COUNT(*) AS n FROM categories WHERE path = 'unused'")["n"] == 0
    assert _row(conn, "SELECT COUNT(*) AS n FROM keywords WHERE word = 'ghost'")["n"] == 0
    assert _row(conn, "SELECT value FROM meta WHERE key = 'great_event_categories'")["value"] == "other"
    conn.close()
