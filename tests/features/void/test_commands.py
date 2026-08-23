from dailydriver.core.database import get_connection_cm
from dailydriver.features.void.commands import log_void


def test_log_requires_description(db_path, ui):
    assert log_void("v") is None
    assert "requires text" in ui.lines[-1]


def test_log_persists_unparsed_text_without_updating_last_action(db_path):
    assert log_void("v met at 13:00 for 2h").startswith("Void logged at")
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT description FROM void_entries").fetchone()
        state = connection.execute("SELECT value FROM meta WHERE key='last_action'").fetchone()
    assert row["description"] == "met at 13:00 for 2h"
    assert state is None
