# tests/test_qada_integration.py
import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.features.qada import _logic


def test_add_entry_persists(isolated_db):
    eid = _logic.add_entry("Fajr", "prayer", "n_days", "1", slot="fajr")
    # Open a new connection and verify
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
    eid = _logic.add_entry("Fasting", "fasting", "daily", None, slot=None)
    _logic.toggle_pause(eid, "1405-03-01", "1405-03-10")
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        row = cur.execute("SELECT paused_from, paused_until FROM qada_entries WHERE id=?", (eid,)).fetchone()
        assert row["paused_from"] == "1405-03-01"
        assert row["paused_until"] == "1405-03-10"


def test_delete_entry_persists(isolated_db):
    eid = _logic.add_entry("ToDelete", "prayer", "daily", None, slot="fajr")
    _logic.delete_entry(eid)
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        row = cur.execute("SELECT id FROM qada_entries WHERE id=?", (eid,)).fetchone()
        assert row is None


def test_edit_entry_persists(isolated_db):
    eid = _logic.add_entry("OldName", "prayer", "daily", None, slot="fajr")
    _logic.edit_entry(eid, name="NewName", interval_type="weekly", interval_value="2")
    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        row = cur.execute("SELECT name, interval_type, interval_value FROM qada_entries WHERE id=?", (eid,)).fetchone()
        assert row["name"] == "NewName"
        assert row["interval_type"] == "weekly"
        assert row["interval_value"] == "2"
