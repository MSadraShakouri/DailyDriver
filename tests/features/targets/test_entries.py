"""Target entry validation, persistence, and lifecycle behavior."""

import sqlite3

import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.features.targets import entries


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"kind": "other", "name": "x"}, "kind must be"),
        ({"kind": "nazr", "name": "x", "target_total": 0}, "target_total"),
        ({"kind": "nazr", "name": "x", "interval_type": "monthly"}, "interval_type"),
        (
            {"kind": "nazr", "name": "x", "interval_type": "weekly", "interval_value": 7},
            "0-6",
        ),
        (
            {"kind": "nazr", "name": "x", "interval_type": "n_days", "interval_value": 0},
            "positive",
        ),
    ],
)
def test_add_rejects_invalid_domain_values(db_path, kwargs, message):
    with pytest.raises(ValueError, match=message):
        entries.add_entry(**kwargs)


def test_add_and_fetch_round_trip(db_path):
    entry_id = entries.add_entry(
        kind="nazr",
        name="Salavat",
        target_total=1000,
        interval_type="weekly",
        interval_value=2,
        target_per_interval=100,
    )
    by_id = entries.get_entry_by_id(entry_id)
    assert by_id == entries.get_entry_by_name("Salavat")
    assert {key: by_id[key] for key in (
        "name",
        "kind",
        "target_total",
        "interval_type",
        "interval_value",
        "target_per_interval",
    )} == {
        "name": "Salavat",
        "kind": "nazr",
        "target_total": 1000,
        "interval_type": "weekly",
        "interval_value": 2,
        "target_per_interval": 100,
    }


def test_names_are_unique(db_path):
    entries.add_entry("nazr", "Repeated")
    with pytest.raises(sqlite3.IntegrityError):
        entries.add_entry("habit", "Repeated")


def test_listing_is_sorted_and_filterable(db_path):
    entries.add_entry("habit", "Zulu")
    entries.add_entry("nazr", "Alpha", target_total=1)
    entries.add_entry("nazr", "Beta", target_total=1)
    assert [entry["name"] for entry in entries.get_all_entries()] == ["Alpha", "Beta", "Zulu"]
    assert [entry["name"] for entry in entries.get_all_entries("nazr")] == ["Alpha", "Beta"]


def test_record_progress_updates_total_and_history(target, today):
    entry = target()
    entries.record_progress(entry["id"], 7, 7, today.strftime("%Y-%m-%d"), 123)
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 7
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT amount, logged_at FROM target_logs").fetchone()
    assert tuple(row) == (7, 123)


def test_pause_then_unpause(target, today):
    entry = target()
    assert "Paused" in entries.toggle_pause(entry["id"], days=3)
    assert entries.get_entry_by_id(entry["id"])["paused_until"] == "1405-06-04"
    assert "Unpaused" in entries.toggle_pause(entry["id"])
    assert entries.get_entry_by_id(entry["id"])["paused_until"] is None


def test_pause_reports_missing_entry(db_path):
    assert entries.toggle_pause(404) == "Entry 404 not found."


@pytest.mark.parametrize(
    ("updates", "message"),
    [
        ({}, "No fields"),
        ({"target_total": 0}, "Target must be positive"),
        ({"interval_type": "monthly"}, "interval_type"),
        ({"interval_type": "weekly", "interval_value": 7}, "0-6"),
        ({"interval_type": "n_days", "interval_value": 0}, "positive"),
    ],
)
def test_edit_validates_changes(target, updates, message):
    entry = target()
    assert message in entries.edit_entry(entry["id"], **updates)


def test_edit_persists_allowed_fields_and_ignores_unknown(target):
    entry = target()
    result = entries.edit_entry(entry["id"], name="New", target_total=200, unknown="ignored")
    updated = entries.get_entry_by_id(entry["id"])
    assert result == "Updated: Salavat"
    assert updated["name"] == "New"
    assert updated["target_total"] == 200
    assert "unknown" not in updated


def test_delete_cascades_logs(target, today):
    entry = target()
    entries.record_progress(entry["id"], 1, 1, today.strftime("%Y-%m-%d"), 123)
    assert entries.delete_entry(entry["id"]) == "Deleted: Salavat"
    assert entries.get_entry_by_id(entry["id"]) is None
    with get_connection_cm(auto=False) as connection:
        assert connection.execute("SELECT COUNT(*) FROM target_logs").fetchone()[0] == 0


def test_edit_and_delete_report_missing_entry(db_path):
    assert entries.edit_entry(404, name="x") == "Entry 404 not found."
    assert entries.delete_entry(404) == "Entry 404 not found."
