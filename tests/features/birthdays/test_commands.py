import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.features.birthdays.commands import add_birthday


def _birthday(name):
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT * FROM birthdays WHERE name=?", (name,)).fetchone()
    return dict(row) if row else None


def test_add_parses_full_and_short_dates(db_path):
    assert add_birthday("bd Alice 1400/2/3 1") == "Birthday added: Alice (1400/02/03) [important]"
    assert add_birthday("bd Bob 4/5") == "Birthday added: Bob (????/04/05)"
    assert (_birthday("Alice")["year"], _birthday("Alice")["remind_level"]) == (1400, 1)
    assert _birthday("Bob")["year"] is None


def test_add_prompts_when_only_name_is_supplied(db_path, ui):
    ui.queue("6", "7", "1390")
    assert add_birthday("bd Charlie") == "Birthday added: Charlie (1390/07/06)"


def test_bare_add_is_fully_interactive(db_path, ui):
    ui.queue("Dana", "8", "9", "1380", "1")
    assert "[important]" in add_birthday("bd")
    assert _birthday("Dana")["month"] == 9


@pytest.mark.parametrize(
    ("command", "responses", "message"),
    [
        ("bd", ("",), None),
        ("bd Name", ("bad", "2", ""), "Invalid numbers."),
        ("bd Name 13/32", (), "Invalid date."),
    ],
)
def test_add_rejects_incomplete_or_invalid_input(db_path, ui, command, responses, message):
    ui.queue(*responses)
    assert add_birthday(command) is None
    if message:
        assert message in ui.lines
