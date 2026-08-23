import jdatetime
import pytest

from dailydriver.features.hygiene import header


def _insert(connection, name, interval, *, early=1, due_today=1):
    connection.execute(
        """INSERT INTO hygiene_config
           (item, desired_interval_days, early_warning_enabled, show_due_today)
           VALUES (?,?,?,?)""",
        (name, interval, early, due_today),
    )
    connection.commit()


@pytest.mark.parametrize(
    ("days_since", "interval", "early", "due_today", "expected"),
    [
        (8, 7, 1, 1, "overdue!"),
        (7, 7, 1, 1, "due today"),
        (7, 7, 1, 0, None),
        (6, 7, 1, 1, "due in 1d"),
        (6, 7, 0, 1, None),
        (13, 15, 1, 1, "due in 2d"),
        (4, 7, 1, 1, None),
    ],
)
def test_nudge_thresholds(db_connection, monkeypatch, days_since, interval, early, due_today, expected):
    today = jdatetime.date(1405, 6, 1)
    _insert(db_connection, "shower", interval, early=early, due_today=due_today)
    monkeypatch.setattr(header, "get_last_hygiene_time", lambda connection, item: 123)
    monkeypatch.setattr(
        header,
        "shift_timestamp_to_date",
        lambda timestamp: today - jdatetime.timedelta(days=days_since),
    )
    lines = header.compute_hygiene_nudges(db_connection, relative_to=today)
    if expected is None:
        assert lines == []
    else:
        assert len(lines) == 1
        assert expected in lines[0]


def test_item_without_history_has_no_nudge(db_connection, monkeypatch):
    _insert(db_connection, "shower", 7)
    monkeypatch.setattr(header, "get_last_hygiene_time", lambda connection, item: None)
    assert header.compute_hygiene_nudges(db_connection, relative_to=jdatetime.date(1405, 6, 1)) == []


def test_header_hook_hides_non_today_and_limits_lines(db_connection, monkeypatch):
    monkeypatch.setattr(header, "get_shifted_today", lambda: jdatetime.date(1405, 6, 1))
    monkeypatch.setattr(header, "compute_hygiene_nudges", lambda *args, **kwargs: ["one", "two", "three"])
    date = jdatetime.date(1405, 6, 1)
    assert header.get_hygiene_lines(db_connection, date, False) == []
    assert header.get_hygiene_lines(db_connection, date, True) == ["one", "two"]
