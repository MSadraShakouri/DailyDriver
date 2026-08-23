# tests/test_qada_integration.py
from dailydriver.core.database import get_connection_cm
from dailydriver.features.qada import entries


def test_add_entry_persists(isolated_db):
    eid = entries.add_entry("Fajr", "prayer", "n_days", "1", slot="fajr")
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        row = cur.execute(
            "SELECT id, name, kind, interval_type, interval_value, slot FROM qada_entries WHERE id=?", (eid,)
        ).fetchone()
        assert row is not None
        assert row["name"] == "Fajr"
        assert row["kind"] == "prayer"
        assert row["interval_type"] == "n_days"
        assert row["interval_value"] == "1"
        assert row["slot"] == "fajr"


def test_toggle_pause_persists(isolated_db):
    eid = entries.add_entry("Fasting", "fasting", "daily", None, slot=None)
    entries.toggle_pause(eid, days=3)
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        row = cur.execute("SELECT paused_until FROM qada_entries WHERE id=?", (eid,)).fetchone()
        assert row["paused_until"] is not None
        # Check it's about 3 days in the future
        from datetime import timedelta

        import jdatetime

        today = jdatetime.date.today()
        pause_date = jdatetime.date(*map(int, row["paused_until"].split("-")))
        assert pause_date == today + timedelta(days=3)


def test_toggle_pause_toggle_off(isolated_db):
    eid = entries.add_entry("Fasting", "fasting", "daily", None, slot=None)
    # Pause
    entries.toggle_pause(eid, days=3)
    # Unpause
    entries.toggle_pause(eid)
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        row = cur.execute("SELECT paused_until FROM qada_entries WHERE id=?", (eid,)).fetchone()
        assert row["paused_until"] is None


def test_delete_entry_persists(isolated_db):
    eid = entries.add_entry("ToDelete", "prayer", "daily", None, slot="fajr")
    entries.delete_entry(eid)
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        row = cur.execute("SELECT id FROM qada_entries WHERE id=?", (eid,)).fetchone()
        assert row is None


def test_edit_entry_persists(isolated_db):
    eid = entries.add_entry("OldName", "prayer", "daily", None, slot="fajr")
    entries.edit_entry(eid, name="NewName", interval_type="weekly", interval_value="2")
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        row = cur.execute("SELECT name, interval_type, interval_value FROM qada_entries WHERE id=?", (eid,)).fetchone()
        assert row["name"] == "NewName"
        assert row["interval_type"] == "weekly"
        assert row["interval_value"] == "2"
