from datetime import datetime, timedelta

import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.features.sleep import commands
from dailydriver.utils.time_parser import TimeInterpretation


def interpretation(start_hour=23, duration=480):
    start = datetime(2026, 8, 22, start_hour)
    end = start + timedelta(minutes=duration)
    return TimeInterpretation(start, end, duration, "test", 0)


@pytest.mark.parametrize(
    ("function", "command", "usage"),
    [
        (commands.log_sleep, "s", "Usage: S"),
        (commands.log_nap, "nap", "Usage: nap"),
    ],
)
def test_range_is_required(db_path, ui, function, command, usage):
    assert function(command) is None
    assert usage in ui.lines[-1]


@pytest.mark.parametrize(
    ("function", "command", "expected_expression"),
    [
        (commands.log_sleep, "s 23:00 07:00", "23:00-07:00"),
        (commands.log_nap, "nap 14:00 14:30", "14:00-14:30"),
        (commands.log_nap, "nap 14:00-14:30", "14:00-14:30"),
    ],
)
def test_old_and_unified_syntax_reach_parser(db_path, ui, monkeypatch, function, command, expected_expression):
    seen = []

    def parse(expression, now, last_time):
        seen.append(expression)
        return []

    monkeypatch.setattr(commands, "parse_time_expressions", parse)
    function(command)
    assert seen == [expected_expression]


def test_sleep_requires_interpretation_with_end(db_path, ui, monkeypatch):
    start = datetime(2026, 8, 22, 23)
    no_end = TimeInterpretation(start, None, None, "single", 0)
    monkeypatch.setattr(commands, "parse_time_expressions", lambda *args, **kwargs: [no_end])
    assert commands.log_sleep("s 23") is None
    assert "Duration required" in ui.lines[-1]


def test_sleep_confirmation_can_cancel(db_path, ui, monkeypatch):
    monkeypatch.setattr(commands, "parse_time_expressions", lambda *args, **kwargs: [interpretation()])
    monkeypatch.setattr(commands.current_ui, "confirm", lambda *args, **kwargs: False)
    assert commands.log_sleep("s 23-7") is None
    with get_connection_cm(auto=False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM sleep_logs").fetchone()[0] == 0


def test_sleep_persists_selected_range(db_path, ui, monkeypatch):
    selected = interpretation()
    monkeypatch.setattr(commands, "parse_time_expressions", lambda *args, **kwargs: [selected])
    monkeypatch.setattr(commands, "today_jalali", lambda: "1405-06-01")
    result = commands.log_sleep("s 23-7")
    assert "8h 0m" in result
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT * FROM sleep_logs").fetchone()
    assert row["jalali_date"] == "1405-06-01"
    assert row["duration_minutes"] == 480
    assert row["sleep_time"] == int(selected.start.timestamp())


def test_nap_persists_selected_range(db_path, ui, monkeypatch):
    selected = interpretation(start_hour=14, duration=25)
    monkeypatch.setattr(commands, "parse_time_expressions", lambda *args, **kwargs: [selected])
    monkeypatch.setattr(commands, "today_jalali", lambda: "1405-06-01")
    assert commands.log_nap("nap 14-14:25") == "Nap logged: 14:00 → 14:25 (0h 25m)"
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT * FROM nap_logs").fetchone()
    assert row["duration_minutes"] == 25
    assert row["description"] is None


def test_last_action_is_forwarded_to_parser(db_path, ui, monkeypatch):
    timestamp = int(datetime(2026, 8, 22, 22).timestamp())
    monkeypatch.setattr(commands, "get_last_action_time", lambda: timestamp)
    seen = []
    monkeypatch.setattr(
        commands,
        "parse_time_expressions",
        lambda expression, now, last_time: seen.append(last_time) or [],
    )
    commands.log_sleep("s l-7")
    assert seen == [datetime.fromtimestamp(timestamp)]
