"""prompt_toolkit completer classes built on the pure completion engine.

Separated from :mod:`dailydriver.ui.completion` so the ``main.py --complete``
shell hook can use the engine without paying for the prompt_toolkit import on
every Tab press. Interactive callers (REPL, inner prompts) import from here.
"""

from __future__ import annotations

from prompt_toolkit.completion import Completer, Completion

from dailydriver.ui.completion import category_paths, split_completion_line, suggest
from dailydriver.ui.fuzzy import rank_matches


class ReplCompleter(Completer):
    """Whole-line completer for the REPL prompt."""

    def __init__(self, command_names: list[str] | set[str] | tuple[str, ...], include_repl_extra: bool = True):
        self.command_names = sorted(set(command_names))
        self.include_repl_extra = include_repl_extra

    def get_completions(self, document, complete_event):
        tokens, word = split_completion_line(document.text_before_cursor)
        for candidate in suggest(tokens, word, self.command_names, self.include_repl_extra):
            yield Completion(candidate, start_position=-len(word))


class CategoryCompleter(Completer):
    """Space-separated multi-entry category completer.

    Each word completes against the category catalog (fuzzy match, best first) while
    already-committed paths are dropped live. Used by prompts that collect
    several categories on one line (e.g. bare ``sge``). Database access is
    deferred until completion actually runs, so plain backends pay nothing.
    """

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        if text.strip() == "":
            committed: list[str] = []
            word = ""
        elif text[-1].isspace():
            committed = text.split()
            word = ""
        else:
            tokens = text.split()
            committed, word = tokens[:-1], tokens[-1]
        chosen = {token.lower() for token in committed}
        available = [path for path in category_paths() if path.lower() not in chosen]
        for path in rank_matches(available, word):
            yield Completion(path, start_position=-len(word))
