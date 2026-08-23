"""Qada entry persistence and lifecycle behavior."""

import jdatetime
import pytest

from dailydriver.features.qada import entries


def test_add_prayer_requires_known_slot(db_path):
    with pytest.raises(ValueError, match="slot must be"):
        entries.add_entry("Morning", "prayer", slot="morning")


def test_add_fetch_and_list_entries(qada_entry):
    fajr = qada_entry()
    fasting = qada_entry(name="Fasting", kind="fasting")
    assert entries.get_entry_by_slot_or_kind(slot="fajr", kind="prayer") == fajr
    assert entries.get_entry_by_slot_or_kind(kind="fasting") == fasting
    assert entries.get_entry_by_slot_or_kind() is None
    assert [entry["name"] for entry in entries.list_entries("prayer")] == ["Fajr"]
    assert {entry["name"] for entry in entries.list_entries()} == {"Fajr", "Fasting"}


def test_resolve_entry_accepts_id_slot_and_name(qada_entry):
    entry = qada_entry(name="My Fajr")
    assert entries.resolve_entry_id(str(entry["id"])) == entry["id"]
    assert entries.resolve_entry_id("fajr") == entry["id"]
    assert entries.resolve_entry_id("My Fajr") == entry["id"]
    assert entries.resolve_entry_id("missing") is None


def test_edit_target_caps_logged_total(qada_entry, db_connection):
    entry = qada_entry(target_total=20)
    db_connection.execute("UPDATE qada_entries SET logged_total=15 WHERE id=?", (entry["id"],))
    db_connection.commit()
    entries.edit_entry(entry["id"], target_total=10, ignored="value")
    updated = entries.get_entry(entry["id"])
    assert (updated["target_total"], updated["logged_total"]) == (10, 10)


def test_edit_with_no_allowed_fields_is_noop(qada_entry):
    entry = qada_entry()
    assert entries.edit_entry(entry["id"], unknown="value") is None
    assert entries.get_entry(entry["id"])["name"] == "Fajr"


def test_pause_toggle_persists(qada_entry):
    entry = qada_entry()
    today = jdatetime.date.today()
    assert "Paused Fajr" in entries.toggle_pause(entry["id"], days=3)
    expected = (today + jdatetime.timedelta(days=3)).strftime("%Y-%m-%d")
    assert entries.get_entry(entry["id"])["paused_until"] == expected
    assert entries.toggle_pause(entry["id"]) == "Unpaused Fajr"
    assert entries.get_entry(entry["id"])["paused_until"] is None


def test_missing_pause_and_fasting_pause_errors(db_path):
    assert entries.toggle_pause(404) == "Entry 404 not found."


def test_delete_removes_entry(qada_entry):
    entry = qada_entry()
    entries.delete_entry(entry["id"])
    assert entries.get_entry(entry["id"]) is None
