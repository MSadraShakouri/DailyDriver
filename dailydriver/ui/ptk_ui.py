"""prompt_toolkit-based input backend.

This backend upgrades *input* only: the REPL prompt gains persistent history
and command autocompletion, and interactive pickers (categories) gain ranked
autocompletion. All output still goes through plain ``print`` via the shared
:class:`UI` base, so headers, tables, and calendars render identically.

Everything here is defensive: if prompt_toolkit raises for any reason (e.g. a
terminal that cannot support it), callers fall back to plain input. The module
only imports prompt_toolkit lazily so that non-interactive paths never pay for
it.
"""

from __future__ import annotations

import os

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter, WordCompleter
from prompt_toolkit.history import FileHistory, InMemoryHistory

from dailydriver.ui.terminal_ui import TerminalUI

# How many lines to reserve below the prompt for the completion dropdown.
# prompt_toolkit defaults to 8 and its menu itself caps at 16 rows. With a short
# 5-item numbered list we can afford to reserve more so the live dropdown shows
# plenty at once, while still keeping the header on screen.
_MENU_LINES = 11


def _history_dir() -> str:
    """Return the directory used to store per-context history files."""
    override = os.environ.get("DAILYDRIVER_DB")
    if override:
        base = os.path.dirname(os.path.abspath(override)) or "."
    else:
        from dailydriver.core.database import PROJECT_ROOT

        base = os.path.join(PROJECT_ROOT, "data")
    path = os.path.join(base, ".history")
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        return ""
    return path


class _RankedCompleter(Completer):
    """Yield ranked matches first, then the rest of a catalog.

    The order of ``ranked`` is preserved (it already reflects the keyword
    system's TF-IDF + exact-boost ordering); remaining catalog entries follow.
    Only entries containing the current word (case-insensitive) are offered.

    Completions already committed on the line are dropped live: a fully typed
    path is excluded, and a fully typed number (e.g. ``3``) resolves through the
    ranked list to its path and excludes that too. Only tokens *before* the word
    currently being typed count as committed, so the in-progress word still
    completes normally.
    """

    def __init__(self, numbered: list[str], ranked: list[str], catalog: list[str]):
        # ``numbered`` maps typed numbers (as shown in the visible list) to paths.
        # ``ranked`` orders the dropdown; the rest of the catalog follows.
        self.numbered = list(numbered)
        self.ranked = list(ranked)
        seen = set(self.ranked)
        self.rest = [item for item in catalog if item not in seen]

    def _already_chosen(self, document) -> set[str]:
        """Paths already committed on the line (by name or by visible number)."""
        text_before = document.text_before_cursor
        # Everything up to the last space is committed; the final chunk is the
        # word still being typed (handled by the normal filter below).
        committed = text_before.rsplit(" ", 1)[0] if " " in text_before else ""
        chosen: set[str] = set()
        for token in committed.split():
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(self.numbered):
                    chosen.add(self.numbered[idx].lower())
            else:
                chosen.add(token.lower())
        return chosen

    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor(WORD=True)
        lowered = word.lower()
        chosen = self._already_chosen(document)
        for item in self.ranked + self.rest:
            if item.lower() in chosen:
                continue
            if lowered in item.lower():
                yield Completion(item, start_position=-len(word))


class PromptToolkitUI(TerminalUI):
    """Terminal UI whose prompts use prompt_toolkit for history/completion.

    Inherits plain output (print) and confirm helpers from :class:`TerminalUI`;
    only ``prompt`` and ``select_categories`` are enriched.
    """

    def __init__(self):
        self._sessions: dict[str, PromptSession] = {}

    def _session(self, history_key: str | None) -> PromptSession:
        key = history_key or "__default__"
        session = self._sessions.get(key)
        if session is None:
            history = InMemoryHistory()
            if history_key:
                hist_dir = _history_dir()
                if hist_dir:
                    history = FileHistory(os.path.join(hist_dir, f"{history_key}.txt"))
            session = PromptSession(history=history)
            self._sessions[key] = session
        return session

    def prompt(self, text: str, completions: list[str] | None = None, history_key: str | None = None) -> str:
        try:
            completer = None
            if completions:
                completer = FuzzyCompleter(WordCompleter(completions, ignore_case=True, sentence=False))
            session = self._session(history_key)
            # Reserve only a few lines for the completion menu so it can show
            # without scrolling already-printed output (the header) off-screen.
            result = session.prompt(
                text,
                completer=completer,
                complete_while_typing=True,
                reserve_space_for_menu=_MENU_LINES,
            )
            return result.strip()
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception:
            # Any prompt_toolkit failure degrades to plain input.
            return super().prompt(text)

    def select_categories(
        self,
        matches: list[tuple[str, float]],
        ranked_paths: list[str],
        all_paths: list[str],
        show_great_only: bool = False,
    ) -> list[str] | None:
        """Autocompleting, ranked, space-separated multi-select category picker.

        - Enter on an empty line always accepts suggestion #1 (never "Great
          Event only"), regardless of whether a great event is active.
        - Otherwise the user types space-separated numbers (from the visible
          list) and/or paths; the live dropdown is ordered by *ranked_paths* and
          drops entries already committed on the line. Brand-new paths may be
          typed freely.
        - "0" is the explicit opt-in for "Great Event only" when offered.

        Returns the selected paths, or ``None`` to let the caller fall back.
        """
        numbered = [path for path, _ in matches]

        if numbered:
            self.print_line()
            self.print_line("Suggested categories (Tab to autocomplete, space-separate to pick several):")
            if show_great_only:
                self.print_line("  [0] Great Event only")
            for index, path in enumerate(numbered, 1):
                self.print_line(f"  [{index}] {path}")
            hint = "Enter=1, numbers or names to select, or type new paths"
            if show_great_only:
                hint = "Enter=1, 0=Great Event only, numbers/names to select, or type new paths"
        else:
            self.print_line()
            self.print_line("No suggestions. Type a category path (Tab to autocomplete) or Enter to skip.")
            hint = None

        if hint:
            self.print_line(hint)

        # The completer orders the dropdown by the longer ranked list and maps
        # its numbers for live removal; the numbers the user *types* map to the
        # short visible list via _resolve_selection.
        completer = _RankedCompleter(numbered, ranked_paths, all_paths)
        try:
            session = self._session("categories")
            raw = session.prompt(
                "> ",
                completer=completer,
                complete_while_typing=True,
                reserve_space_for_menu=_MENU_LINES,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception:
            return None

        return self._resolve_selection(raw, numbered, show_great_only)

    @staticmethod
    def _resolve_selection(raw: str, numbered: list[str], show_great_only: bool) -> list[str]:
        """Resolve typed input to paths.

        Empty input always accepts suggestion #1 (never "Great Event only").
        "0" is the explicit opt-in for great-event-only. Numbers map to the
        visible numbered list; anything else is treated as a path. Duplicates
        (e.g. typing both ``3`` and its path) are collapsed while preserving
        order.
        """
        choice = raw.strip()
        if choice == "":
            return [numbered[0]] if numbered else []

        if choice.lower() == "0" and show_great_only:
            return []

        selected: list[str] = []
        seen: set[str] = set()

        def add(path: str) -> None:
            if path not in seen:
                seen.add(path)
                selected.append(path)

        for token in choice.split():
            if token == "0" and show_great_only:
                return []
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(numbered):
                    add(numbered[idx])
            else:
                add(token.lower())
        return selected
