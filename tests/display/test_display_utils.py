"""Tests for ANSI-aware wrapping and truncation helpers."""

from __future__ import annotations

import dailydriver.display.display_utils as display_utils
from dailydriver.display.display_utils import (
    display_width,
    pline_wrap,
    strip_ansi,
    truncate_display,
)

REVERSE = "\033[7m"
RESET = "\033[0m"


def _set_width(monkeypatch, width: int) -> None:
    monkeypatch.setattr(display_utils, "get_width", lambda: width)


def test_truncate_display_plain_text():
    assert truncate_display("hello world", 5) == "hello"
    assert truncate_display("hi", 10) == "hi"


def test_truncate_display_keeps_ansi_and_appends_reset():
    text = f"{REVERSE}matchedmatchedmatched{RESET} tail"
    result = truncate_display(text, 10)
    assert display_width(result) == 10
    assert strip_ansi(result) == "matchedmat"
    assert result.endswith(RESET)


def test_truncate_display_counts_wide_chars():
    # Emoji are two columns wide; truncation must respect display width.
    result = truncate_display("💤💤💤", 4)
    assert result == "💤💤"


def test_pline_wrap_truncation_does_not_leak_ansi(monkeypatch, ui):
    _set_width(monkeypatch, 50)
    word = f"{REVERSE}{'x' * 40}{RESET}"
    pline_wrap(" ".join([word] * 5), indent=2, max_lines=2)
    assert len(ui.lines) == 2
    for line in ui.lines:
        assert display_width(line) <= 50
    # The truncated last line must not leave reverse-video open.
    last = ui.lines[-1]
    assert last.endswith("…")
    assert RESET in last or REVERSE not in last


def test_pline_wrap_truncation_marks_ellipsis(monkeypatch, ui):
    _set_width(monkeypatch, 20)
    pline_wrap("aaaa bbbb cccc dddd eeee ffff gggg", indent=0, max_lines=1)
    assert len(ui.lines) == 1
    assert ui.lines[0].endswith("…")
    assert display_width(ui.lines[0]) <= 20
