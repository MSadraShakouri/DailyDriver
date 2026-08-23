from dailydriver.core.database import get_connection_cm
from dailydriver.features.intentions.commands import add_intention


def _rows():
    with get_connection_cm(auto=False) as connection:
        return [dict(row) for row in connection.execute("SELECT * FROM intentions")]


def test_inline_intention_persists_description_only(db_path):
    assert add_intention("t finish report") == "Intention added:\n  finish report"
    row = _rows()[0]
    assert row["description"] == "finish report"
    assert row["deadline"] is None
    assert row["expected_duration_minutes"] is None


def test_interactive_intention_parses_deadline_and_duration(db_path, ui):
    ui.queue("Call family", "1405/06/01", "30")
    result = add_intention("t")
    row = _rows()[0]
    assert row["deadline"] is not None
    assert row["expected_duration_minutes"] == 30
    assert "Expected: 30 min" in result


def test_interactive_intention_ignores_invalid_optional_values(db_path, ui):
    ui.queue("Call family", "invalid", "many")
    add_intention("t")
    row = _rows()[0]
    assert row["deadline"] is None
    assert row["expected_duration_minutes"] is None
    assert "Invalid date. Ignoring deadline." in ui.lines
    assert "Invalid number. Ignoring." in ui.lines


def test_empty_description_cancels(db_path, ui):
    ui.queue("")
    assert add_intention("t") is None
    assert _rows() == []
