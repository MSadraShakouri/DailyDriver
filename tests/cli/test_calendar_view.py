# tests/cli/test_calendar_view.py
"""Tests for ``cal`` argument handling (dispatcher string form + legacy list form)."""

import jdatetime

from dailydriver.cli.calendar_view import show_calendar


def _header_lines(ui):
    return "\n".join(ui.lines)


def test_bare_cal_shows_current_month(ui):
    show_calendar("cal")
    today = jdatetime.date.today()
    assert str(today.year) in _header_lines(ui)


def test_cal_with_month_number(ui):
    show_calendar("cal 6")
    assert "Shahrivar" in _header_lines(ui)


def test_cal_with_month_and_year(ui):
    show_calendar("cal 6 1405")
    text = _header_lines(ui)
    assert "Shahrivar" in text
    assert "1405" in text


def test_cal_with_month_name(ui):
    show_calendar("cal Mehr")
    assert "Mehr" in _header_lines(ui)


def test_cal_with_month_abbreviation(ui):
    show_calendar("cal meh")
    assert "Mehr" in _header_lines(ui)


def test_cal_with_invalid_month_number(ui):
    show_calendar("cal 13")
    assert "Invalid month" in _header_lines(ui)


def test_cal_with_unknown_month_name(ui):
    show_calendar("cal foo")
    assert "Invalid month" in _header_lines(ui)


def test_cal_accepts_legacy_list_args(ui):
    show_calendar(["6", "1405"])
    text = _header_lines(ui)
    assert "Shahrivar" in text
    assert "1405" in text


def test_cal_accepts_none(ui):
    show_calendar(None)
    today = jdatetime.date.today()
    assert str(today.year) in _header_lines(ui)
