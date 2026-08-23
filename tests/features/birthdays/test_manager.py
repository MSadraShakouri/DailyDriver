from dailydriver.core.database import get_connection_cm
from dailydriver.features.birthdays.commands import add_birthday
from dailydriver.features.birthdays.manager import _word_wrap, manage_birthdays


def test_word_wrap_preserves_words():
    assert _word_wrap("alpha beta gamma", 10) == ["alpha beta", "gamma"]


def test_empty_manager_quits(db_path, ui):
    ui.queue("q")
    manage_birthdays()
    assert "No birthdays yet." in ui.lines


def test_manager_toggles_reminder_level(db_path, ui):
    add_birthday("bd Alice 1400/1/1")
    with get_connection_cm(auto=False) as connection:
        identifier = connection.execute("SELECT id FROM birthdays WHERE name='Alice'").fetchone()[0]
    ui.queue(f"t {identifier}", "", "q")
    manage_birthdays()
    with get_connection_cm(auto=False) as connection:
        level = connection.execute("SELECT remind_level FROM birthdays WHERE id=?", (identifier,)).fetchone()[0]
    assert level == 1
    assert any("important" in line for line in ui.lines)
