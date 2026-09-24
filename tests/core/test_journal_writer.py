from dailydriver.core.database import get_connection_cm
from dailydriver.core.journal.writer import inject_great_categories, save_entry
from dailydriver.core.state import start_great_event, start_numbered_state


def test_save_entry_materializes_any_missing_category_path(db_path):
    with get_connection_cm(auto=False) as conn:
        save_entry(conn, "commute", 100, 10, ["transport/car", "transport/car"])
        conn.commit()

    with get_connection_cm(auto=False) as conn:
        categories = conn.execute("SELECT id, path FROM categories").fetchall()
        associations = conn.execute("SELECT category_id FROM entry_categories").fetchall()
    assert [row["path"] for row in categories] == ["transport/car"]
    assert len(associations) == 1


def test_numbered_states_and_great_events_are_automatically_linked(db_path):
    start_numbered_state(1, ["work/focus", "transport/car"])
    start_numbered_state(2, ["friends/a", "work/focus"])
    start_great_event(["work/focus", "legacy/event"])

    selected = ["manual/category"]
    inject_great_categories(selected)
    assert selected == ["manual/category", "work/focus", "legacy/event", "transport/car", "friends/a"]

    with get_connection_cm(auto=False) as conn:
        save_entry(conn, "combine tasks", 100, 10, selected)
        conn.commit()

    with get_connection_cm(auto=False) as conn:
        rows = conn.execute(
            """
            SELECT c.path
            FROM entry_categories ec
            JOIN categories c ON c.id = ec.category_id
            JOIN entries e ON e.id = ec.entry_id
            WHERE e.description = 'combine tasks'
            ORDER BY c.path
            """
        ).fetchall()
    assert {row["path"] for row in rows} == {
        "manual/category",
        "work/focus",
        "legacy/event",
        "transport/car",
        "friends/a",
    }
