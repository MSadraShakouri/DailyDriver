"""Tests for the prompt_toolkit backend's pure logic and fallback wiring."""

from __future__ import annotations

from prompt_toolkit.document import Document

from dailydriver.ui.ptk_ui import PromptToolkitUI, _RankedCompleter
from dailydriver.ui.terminal_ui import TerminalUI, select_ui


class TestResolveSelection:
    def test_empty_picks_top_ranked(self):
        assert PromptToolkitUI._resolve_selection("", ["a/b", "c/d"], False) == ["a/b"]

    def test_empty_with_no_matches_returns_empty(self):
        assert PromptToolkitUI._resolve_selection("", [], False) == []

    def test_numbers_map_to_ranked(self):
        assert PromptToolkitUI._resolve_selection("2", ["a/b", "c/d"], False) == ["c/d"]

    def test_mixed_numbers_and_new_paths(self):
        result = PromptToolkitUI._resolve_selection("1 new/topic", ["a/b", "c/d"], False)
        assert result == ["a/b", "new/topic"]

    def test_new_path_is_lowercased(self):
        assert PromptToolkitUI._resolve_selection("Work/Code", ["a/b"], False) == ["work/code"]

    def test_zero_selects_great_only_when_offered(self):
        assert PromptToolkitUI._resolve_selection("0", ["a/b"], True) == []

    def test_zero_is_literal_when_great_not_offered(self):
        # "0" is not a valid index (0-based -1), so it maps to nothing.
        assert PromptToolkitUI._resolve_selection("0", ["a/b"], False) == []

    def test_out_of_range_number_ignored(self):
        assert PromptToolkitUI._resolve_selection("9", ["a/b"], False) == []


class TestRankedCompleter:
    def test_ranked_come_before_rest(self):
        completer = _RankedCompleter(["work/code", "work/email"], ["work/code", "work/email", "misc/note"])
        completions = [c.text for c in completer.get_completions(Document("work"), None)]
        assert completions == ["work/code", "work/email"]

    def test_filters_by_word(self):
        completer = _RankedCompleter(["work/code"], ["work/code", "misc/note"])
        completions = [c.text for c in completer.get_completions(Document("misc"), None)]
        assert completions == ["misc/note"]

    def test_case_insensitive(self):
        completer = _RankedCompleter(["Work/Code"], ["Work/Code"])
        completions = [c.text for c in completer.get_completions(Document("work"), None)]
        assert completions == ["Work/Code"]


class TestSelectUiFallback:
    def test_non_tty_selects_plain_backend(self):
        # The test environment is not an interactive TTY, so select_ui must
        # return the plain TerminalUI (never crash).
        assert isinstance(select_ui(), TerminalUI)
