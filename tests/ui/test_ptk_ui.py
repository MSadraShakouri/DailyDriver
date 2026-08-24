"""Tests for the prompt_toolkit backend's pure logic and fallback wiring."""

from __future__ import annotations

from prompt_toolkit.document import Document

from dailydriver.ui.ptk_ui import PromptToolkitUI, _RankedCompleter
from dailydriver.ui.terminal_ui import TerminalUI, select_ui


def _completer(numbered, ranked, catalog):
    return _RankedCompleter(numbered, ranked, catalog)


def _complete(completer, text):
    return [c.text for c in completer.get_completions(Document(text), None)]


class TestResolveSelection:
    def test_empty_picks_first(self):
        assert PromptToolkitUI._resolve_selection("", ["a/b", "c/d"], False) == ["a/b"]

    def test_empty_never_picks_great_only_even_when_offered(self):
        # Enter on empty always means #1, regardless of great-event state.
        assert PromptToolkitUI._resolve_selection("", ["a/b", "c/d"], True) == ["a/b"]

    def test_empty_with_no_matches_returns_empty(self):
        assert PromptToolkitUI._resolve_selection("", [], False) == []

    def test_numbers_map_to_visible_list(self):
        assert PromptToolkitUI._resolve_selection("2", ["a/b", "c/d"], False) == ["c/d"]

    def test_mixed_numbers_and_new_paths(self):
        result = PromptToolkitUI._resolve_selection("1 new/topic", ["a/b", "c/d"], False)
        assert result == ["a/b", "new/topic"]

    def test_new_path_is_lowercased(self):
        assert PromptToolkitUI._resolve_selection("Work/Code", ["a/b"], False) == ["work/code"]

    def test_duplicate_number_and_path_collapsed(self):
        # Typing both "1" and its path must not add it twice.
        assert PromptToolkitUI._resolve_selection("1 a/b", ["a/b", "c/d"], False) == ["a/b"]

    def test_zero_selects_great_only_when_offered(self):
        assert PromptToolkitUI._resolve_selection("0", ["a/b"], True) == []

    def test_zero_is_literal_when_great_not_offered(self):
        assert PromptToolkitUI._resolve_selection("0", ["a/b"], False) == []

    def test_out_of_range_number_ignored(self):
        assert PromptToolkitUI._resolve_selection("9", ["a/b"], False) == []


class TestRankedCompleter:
    def test_ranked_come_before_rest(self):
        c = _completer(["work/code", "work/email"], ["work/code", "work/email"], ["work/code", "work/email", "misc/x"])
        assert _complete(c, "work") == ["work/code", "work/email"]

    def test_filters_by_current_word(self):
        c = _completer(["work/code"], ["work/code"], ["work/code", "misc/note"])
        assert _complete(c, "misc") == ["misc/note"]

    def test_case_insensitive(self):
        c = _completer(["Work/Code"], ["Work/Code"], ["Work/Code"])
        assert _complete(c, "work") == ["Work/Code"]

    def test_dropdown_ordered_by_ranked_beyond_numbered(self):
        # numbered (visible) is short; the dropdown still orders by the longer
        # ranked list, then the alphabetical rest.
        numbered = ["a/one"]
        ranked = ["a/one", "a/two", "a/three"]
        catalog = ["a/one", "a/two", "a/three", "a/zzz"]
        c = _completer(numbered, ranked, catalog)
        assert _complete(c, "a") == ["a/one", "a/two", "a/three", "a/zzz"]


class TestLiveRemoval:
    def test_committed_path_removed_from_dropdown(self):
        c = _completer(["work/code", "work/email"], ["work/code", "work/email"], ["work/code", "work/email"])
        # "work/code " is committed (trailing space), typing "work" next.
        assert _complete(c, "work/code work") == ["work/email"]

    def test_committed_number_removes_its_path(self):
        # "1" committed -> maps to numbered[0] == work/code, which drops out.
        c = _completer(["work/code", "work/email"], ["work/code", "work/email"], ["work/code", "work/email"])
        assert _complete(c, "1 work") == ["work/email"]

    def test_in_progress_word_not_treated_as_committed(self):
        # Only tokens before the last space are committed; the typed word still
        # completes.
        c = _completer(["work/code"], ["work/code"], ["work/code"])
        assert _complete(c, "work/co") == ["work/code"]


class TestSelectUiFallback:
    def test_non_tty_selects_plain_backend(self):
        assert isinstance(select_ui(), TerminalUI)
