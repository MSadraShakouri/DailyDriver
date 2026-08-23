import jdatetime
import pytest

from dailydriver.features.presentation import (
    format_due_date,
    format_interval,
    format_percentage,
    is_paused,
    parse_jalali_date,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "0%"), (12, "12%"), (12.345, "12.35%"), (100, "100%")],
)
def test_format_percentage(value, expected):
    assert format_percentage(value) == expected


@pytest.mark.parametrize(
    ("offset", "expected"),
    [(-1, "Overdue"), (0, "today"), (1, "tomorrow"), (3, "in 3 days")],
)
def test_format_due_date(offset, expected):
    today = jdatetime.date(1405, 6, 1)
    assert format_due_date(today + jdatetime.timedelta(days=offset), today) == expected
    assert format_due_date(None, today) == "-"


@pytest.mark.parametrize(
    ("entry", "expected"),
    [
        ({"interval_type": "daily"}, "daily"),
        ({"interval_type": "n_days", "interval_value": 3}, "every 3 days"),
        ({"interval_type": "weekly", "interval_value": 0}, "weekly on Saturday"),
        ({"interval_type": "weekly", "interval_value": 99}, "weekly on 99"),
        ({"interval_type": "monthly", "interval_value": "1,15"}, "monthly on 1,15"),
        ({"interval_type": "custom"}, "custom"),
    ],
)
def test_format_interval(entry, expected):
    assert format_interval(entry) == expected


def test_parse_date_and_pause_state():
    today = jdatetime.date(1405, 6, 1)
    assert parse_jalali_date("1405-06-01") == today
    assert parse_jalali_date("invalid") is None
    assert parse_jalali_date(None) is None
    assert is_paused({"paused_until": "1405-06-01"}, today)
    assert not is_paused({"paused_until": "1405-05-31"}, today)
