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
    """

    def __init__(self, ranked: list[str], catalog: list[str]):
        self.ranked = list(ranked)
        seen = set(self.ranked)
        self.rest = [item for item in catalog if item not in seen]

    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor(WORD=True)
        lowered = word.lower()
        for item in self.ranked + self.rest:
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
            # reserve_space_for_menu=0 keeps the prompt inline: prompt_toolkit
            # otherwise pre-reserves space for the completion menu, scrolling
            # already-printed output (the header) off-screen. The menu still
            # opens on demand; we only change input, never wipe output.
            result = session.prompt(
                text,
                completer=completer,
                complete_while_typing=True,
                reserve_space_for_menu=0,
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
        all_paths: list[str],
        show_great_only: bool = False,
    ) -> list[str] | None:
        """Autocompleting, ranked, space-separated multi-select category picker.

        - Enter on an empty line accepts the top-ranked suggestion (or, when
          ``show_great_only`` is set and there are matches, "Great Event only").
        - Otherwise the user types space-separated paths; ranked suggestions are
          offered first via autocompletion, and brand-new paths may be typed
          freely.
        - "0" selects "Great Event only" when offered.

        Returns the selected paths, or ``None`` to let the caller fall back.
        """
        ranked_paths = [path for path, _ in matches]

        # Show the ranked suggestions so the user sees the same list as before.
        if ranked_paths:
            self.print_line()
            self.print_line("Suggested categories (Tab to autocomplete, space-separate to pick several):")
            if show_great_only:
                self.print_line("  [0] Great Event only")
            for index, path in enumerate(ranked_paths, 1):
                self.print_line(f"  [{index}] {path}")
            hint = "Enter=top suggestion, numbers or names to select, or type new paths"
            if show_great_only:
                hint = "Enter=top, 0=Great Event only, numbers/names to select, or type new paths"
        else:
            self.print_line()
            self.print_line("No suggestions. Type a category path (Tab to autocomplete) or Enter to skip.")
            hint = None

        if hint:
            self.print_line(hint)

        completer = _RankedCompleter(ranked_paths, all_paths)
        try:
            session = self._session("categories")
            raw = session.prompt(
                "> ",
                completer=completer,
                complete_while_typing=True,
                reserve_space_for_menu=0,
            ).strip()
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception:
            return None

        return self._resolve_selection(raw, ranked_paths, show_great_only)

    @staticmethod
    def _resolve_selection(raw: str, ranked_paths: list[str], show_great_only: bool) -> list[str]:
        choice = raw.strip()
        if choice == "":
            return [ranked_paths[0]] if ranked_paths else []

        lowered = choice.lower()
        if lowered == "0" and show_great_only:
            return []

        selected: list[str] = []
        for token in choice.split():
            if token == "0" and show_great_only:
                return []
            if token.isdigit():
                idx = int(token) - 1
                if 0 <= idx < len(ranked_paths):
                    selected.append(ranked_paths[idx])
            else:
                selected.append(token.lower())
        return selected
