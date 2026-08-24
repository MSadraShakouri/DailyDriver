import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.features.birthdays.commands import add_birthday


def _birthday(name):
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT * FROM birthdays WHERE name=?", (name,)).fetchone()
    return dict(row) if row else None


def test_add_is_fully_interactive(db_path, ui):
    # name, day, month, year, reminder level
    ui.queue("Alice", "3", "2", "1400", "1")
    assert add_birthday("bd") == "Birthday added: Alice (1400/02/03) [important]"
    row = _birthday("Alice")
    assert (row["day"], row["month"], row["year"], row["remind_level"]) == (3, 2, 1400, 1)


def test_add_without_year_or_reminder(db_path, ui):
    ui.queue("Bob", "5", "4", "", "")
    assert add_birthday("bd") == "Birthday added: Bob (????/04/05)"
    assert _birthday("Bob")["year"] is None
    assert _birthday("Bob")["remind_level"] == 0


def test_inline_arguments_are_ignored(db_path, ui):
    # As of v2.0 any inline args are ignored; prompts still drive creation.
    ui.queue("Charlie", "7", "6", "1390", "")
    assert add_birthday("bd Ali 1386/05/12") == "Birthday added: Charlie (1390/06/07)"
    assert _birthday("Ali") is None
    assert _birthday("Charlie")["month"] == 6


def test_empty_name_cancels(db_path, ui):
    ui.queue("")
    assert add_birthday("bd") is None


@pytest.mark.parametrize(
    ("responses", "message"),
    [
        (("Name", "bad", "2", "", ""), "Invalid numbers."),
        (("Name", "32", "13", "", ""), "Invalid date."),
    ],
)
def test_add_rejects_invalid_input(db_path, ui, responses, message):
    ui.queue(*responses)
    assert add_birthday("bd") is None
    assert message in ui.lines
