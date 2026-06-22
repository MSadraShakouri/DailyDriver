# tests/test_qada_slot.py
import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.features.qada import _logic


def test_add_prayer_entry_valid_slot_succeeds(isolated_db):
    eid = _logic.add_entry("Fajr", "prayer", "n_days", "1", slot="fajr")
    assert eid is not None
    with get_connection_cm(auto=False) as conn:
        row = conn.execute("SELECT slot FROM qada_entries WHERE id=?", (eid,)).fetchone()
        assert row["slot"] == "fajr"


def test_add_prayer_entry_invalid_slot_raises(isolated_db):
    with pytest.raises(ValueError, match="slot must be one of"):
        _logic.add_entry("Morning", "prayer", "n_days", "1", slot="morning")


def test_add_fasting_entry_ignores_slot(isolated_db):
    eid = _logic.add_entry("Ramadan", "fasting", "daily", None, slot=None)
    assert eid is not None
    with get_connection_cm(auto=False) as conn:
        row = conn.execute("SELECT slot FROM qada_entries WHERE id=?", (eid,)).fetchone()
        assert row["slot"] is None


def test_resolve_entry_id_looks_up_by_slot_first(isolated_db):
    eid = _logic.add_entry("My Fajr", "prayer", "n_days", "1", slot="fajr")
    resolved = _logic.resolve_entry_id("fajr")
    assert resolved == eid
    # Also works by name
    resolved2 = _logic.resolve_entry_id("My Fajr")
    assert resolved2 == eid


def test_resolve_entry_id_falls_back_to_name(isolated_db):
    eid = _logic.add_entry("Ramadan", "fasting", "daily", None, slot=None)
    resolved = _logic.resolve_entry_id("Ramadan")
    assert resolved == eid
