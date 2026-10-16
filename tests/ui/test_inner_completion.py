# tests/ui/test_inner_completion.py
"""Tests for completion inside commands (viewers, selectors, sge prompt)."""

from collections import deque

import pytest
from prompt_toolkit.document import Document

from dailydriver.core.database import get_connection_cm
from dailydriver.ui.completion import (
    BROWSER_NAV,
    DAY_VIEW_NAV,
    PRAYER_SLOT_CHOICES,
    clear_completion_cache,
)
from dailydriver.ui.completion_ptk import CategoryCompleter
from dailydriver.ui.terminal_ui import current_ui


class PromptSpy:
    """Records prompt() kwargs while serving canned responses."""

    def __init__(self, *responses):
        self.responses = deque(responses)
        self.calls: list[dict] = []

    def __call__(self, text="", completions=None, history_key=None):
        self.calls.append({"text": text, "completions": completions})
        return self.responses.popleft() if self.responses else ""


@pytest.fixture
def prompt_spy(monkeypatch):
    spy = PromptSpy()
    monkeypatch.setattr(current_ui, "prompt", spy)
    monkeypatch.setattr(current_ui, "print_line", lambda *a, **k: None)
    monkeypatch.setattr(current_ui, "clear", lambda: None)
    return spy


@pytest.fixture(autouse=True)
def clean_cache(db_path):
    clear_completion_cache()
    yield
    clear_completion_cache()


def _seed_categories(*paths):
    with get_connection_cm(auto=False) as conn:
        for path in paths:
            conn.execute("INSERT INTO categories (path) VALUES (?)", (path,))
        conn.commit()


def _seed_entry(description="morning running session"):
    import time

    with get_connection_cm(auto=False) as conn:
        conn.execute(
            "INSERT INTO entries (created_at, started_at, duration_minutes, description) VALUES (?,?,?,?)",
            (int(time.time()), int(time.time()), 30, description),
        )
        conn.commit()


def _complete(completer, text):
    return [c.text for c in completer.get_completions(Document(text), None)]


# ── CategoryCompleter ────────────────────────────────────────────────


def test_category_completer_matches_substring(db_path):
    _seed_categories("work/code", "rest/nap")
    assert _complete(CategoryCompleter(), "cod") == ["work/code"]
    assert set(_complete(CategoryCompleter(), "")) == {"work/code", "rest/nap"}


def test_category_completer_drops_committed_paths(db_path):
    _seed_categories("work/code", "work/email")
    assert _complete(CategoryCompleter(), "work/code ") == ["work/email"]
    # Partial second word still completes normally.
    assert _complete(CategoryCompleter(), "work/code em") == ["work/email"]


def test_category_completer_positions_replacement(db_path):
    _seed_categories("work/code", "work/email")
    [completion] = list(CategoryCompleter().get_completions(Document("work/code em"), None))
    assert completion.text == "work/email"
    assert completion.start_position == -len("em")


# ── Wiring: prompts receive completers ───────────────────────────────


def test_sge_prompt_offers_categories(prompt_spy, db_path):
    from dailydriver.cli.commands.events import start_great_event_cmd

    prompt_spy.responses.extend(["work/code"])
    start_great_event_cmd("sge")
    assert len(prompt_spy.calls) == 1
    assert isinstance(prompt_spy.calls[0]["completions"], CategoryCompleter)


def test_day_view_nav_offers_navigation(prompt_spy, db_path):
    from dailydriver.cli.day_view import show_day

    prompt_spy.responses.extend(["q"])
    show_day("day")
    assert prompt_spy.calls[0]["completions"] == list(DAY_VIEW_NAV)


def test_entry_viewer_offers_browser_nav(prompt_spy, db_path):
    from dailydriver.cli.entry_viewer import view_entries

    _seed_entry()
    prompt_spy.responses.extend(["q"])
    view_entries()
    assert prompt_spy.calls[0]["completions"] == list(BROWSER_NAV)


def test_search_view_offers_browser_nav(prompt_spy, db_path):
    from dailydriver.cli.search_view import search

    _seed_entry("morning running session")
    prompt_spy.responses.extend(["q"])
    search("search running")
    assert prompt_spy.calls[0]["completions"] == list(BROWSER_NAV)


def test_prayer_slot_selector_offers_choices(prompt_spy, db_connection):
    from dailydriver.features.prayer.commands import _travel_mode_select_slot

    prompt_spy.responses.extend([""])
    slot = _travel_mode_select_slot(db_connection, "1405-01-01")
    assert slot == "fajr"
    assert prompt_spy.calls[0]["completions"] == list(PRAYER_SLOT_CHOICES)
