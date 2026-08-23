import time
from datetime import datetime

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.features.qada import entries, schedule


def _log(entry_id, date, amount=1):
    with get_connection_cm(auto=False) as connection:
        connection.execute(
            "INSERT INTO qada_logs (entry_id, amount, instance_date, logged_at) VALUES (?,?,?,?)",
            (entry_id, amount, date.strftime("%Y-%m-%d"), int(time.time())),
        )
        connection.commit()


def test_first_pending_instance_is_reference_date(qada_entry):
    today = jdatetime.date.today()
    entry = qada_entry(interval_type="n_days", interval_value="3")
    assert schedule.compute_pending_instance(entry, today) == today


def test_next_instance_uses_last_log_not_amount(qada_entry):
    today = jdatetime.date.today()
    entry = qada_entry(interval_type="n_days", interval_value="3")
    _log(entry["id"], today, amount=20)
    assert schedule.compute_pending_instance(entry, today) == today + jdatetime.timedelta(days=3)


def test_paused_entry_has_no_pending_instance(qada_entry):
    today = jdatetime.date.today()
    entry = qada_entry()
    entries.edit_entry(entry["id"], paused_until=(today + jdatetime.timedelta(days=1)).strftime("%Y-%m-%d"))
    paused = entries.get_entry(entry["id"])
    assert schedule.compute_pending_instance(paused, today) is None
    assert schedule.get_current_pending_instance(paused, today) is None


def test_completed_entry_has_no_current_pending_instance(qada_entry):
    entry = qada_entry(target_total=1)
    entries.edit_entry(entry["id"], target_total=0)
    assert schedule.get_current_pending_instance(entries.get_entry(entry["id"]), jdatetime.date.today()) is None


def test_current_pending_finds_oldest_unlogged_date(qada_entry, db_connection):
    today = jdatetime.date.today()
    yesterday = today - jdatetime.timedelta(days=1)
    entry = qada_entry()
    gregorian = yesterday.togregorian()
    created = int(datetime(gregorian.year, gregorian.month, gregorian.day, 12).timestamp())
    db_connection.execute("UPDATE qada_entries SET created_at=? WHERE id=?", (created, entry["id"]))
    db_connection.commit()
    refreshed = entries.get_entry(entry["id"])
    assert schedule.get_current_pending_instance(refreshed, today) == yesterday
    _log(entry["id"], yesterday)
    assert schedule.get_current_pending_instance(refreshed, today) == today


def test_private_log_queries_return_expected_values(qada_entry):
    today = jdatetime.date.today()
    entry = qada_entry()
    assert schedule._get_last_log_date(entry["id"]) is None
    _log(entry["id"], today)
    assert schedule._get_last_log_date(entry["id"]) == today
    assert schedule._is_instance_logged(entry["id"], today)
