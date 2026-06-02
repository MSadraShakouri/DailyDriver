# tests/test_keyword_learner.py
import unittest

from dailydriver.core.keyword_learner import tokenize


class TestKeywordTokenizer(unittest.TestCase):
    def test_numeric_time_discarded(self):
        self.assertEqual(tokenize("00:55"), [])

    def test_two_letter_words_discarded(self):
        self.assertEqual(tokenize("2-3"), [])

    def test_mixed_content(self):
        tokens = tokenize("coffee break")
        self.assertIn("coffe", tokens)
        self.assertIn("break", tokens)

    def test_stop_words_and_short_filtered(self):
        tokens = tokenize("last 20 mins")
        self.assertEqual(tokens, [])  # all stop words or short

    def test_hyphenated_numeric_range(self):
        tokens = tokenize("worked on project 9-12")
        self.assertIn("work", tokens)
        self.assertIn("project", tokens)
        self.assertNotIn("9", tokens)
        self.assertNotIn("12", tokens)

    def test_stop_word_in_middle(self):
        tokens = tokenize("hello was world")
        self.assertIn("hello", tokens)
        self.assertIn("world", tokens)
        self.assertNotIn("was", tokens)

    def test_minimum_length_three(self):
        tokens = tokenize("to be or not to be")
        self.assertEqual(tokens, [])  # all short or stop


def test_save_entry_learns_keywords():
    import sqlite3
    import time

    from dailydriver.core.entry_writer import _save_entry

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE categories (id INTEGER PRIMARY KEY, path TEXT UNIQUE)")
    conn.execute(
        "CREATE TABLE keywords (id INTEGER PRIMARY KEY, word TEXT, category_id INTEGER, count INTEGER DEFAULT 1)"
    )
    conn.execute(
        "CREATE TABLE entries (id INTEGER PRIMARY KEY, created_at INTEGER, started_at INTEGER, duration_minutes INTEGER, description TEXT)"
    )
    conn.execute("CREATE TABLE entry_categories (entry_id INTEGER, category_id INTEGER)")
    conn.execute("CREATE VIRTUAL TABLE entries_fts USING fts5(description, content='entries', content_rowid='id')")
    conn.commit()

    # Insert a category
    conn.execute("INSERT INTO categories (path) VALUES ('test/cat')")
    conn.commit()

    # Call _save_entry
    result = _save_entry(conn, "test entry words", int(time.time()), 5, ["test/cat"])
    assert result is not None

    # Verify keywords were learned
    rows = conn.execute("SELECT word FROM keywords WHERE category_id=1").fetchall()
    words = {r["word"] for r in rows}
    assert words >= {"test", "entri", "word"}


if __name__ == "__main__":
    unittest.main()
