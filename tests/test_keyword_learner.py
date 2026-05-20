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


if __name__ == "__main__":
    unittest.main()
