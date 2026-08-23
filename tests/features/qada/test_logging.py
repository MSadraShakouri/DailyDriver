"""Qada progress logging uses real persisted entries and logs."""

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.features.qada import entries, logging


def test_prayer_log_updates_total_and_caps_amount(qada_entry):
    entry = qada_entry(target_total=4)
    assert "4/4 (100.000%)" in logging.log_prayer_qada(entry["id"], 10, now=123)
    updated = entries.get_entry(entry["id"])
    assert updated["logged_total"] == 4
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT amount, logged_at FROM qada_logs").fetchone()
    assert tuple(row) == (4, 123)


def test_prayer_log_rejects_missing_unset_and_complete_entries(qada_entry):
    assert logging.log_prayer_qada(404, 1) == "Entry not found."
    unset = qada_entry(name="Unset", slot="dhuhr_asr", target_total=-1)
    assert "Target is not set" in logging.log_prayer_qada(unset["id"], 1)
    complete = qada_entry(name="Complete", slot="maghrib_isha", target_total=1)
    logging.log_prayer_qada(complete["id"], 1)
    assert logging.log_prayer_qada(complete["id"], 1) == "Already at target. Nothing to log."


def test_fasting_log_uses_today_and_supplied_timestamp(qada_entry):
    entry = qada_entry(name="Fasting", kind="fasting", target_total=2)
    result = logging.log_fasting(entry["id"], now=456)
    assert "Fasting: 1/2 (50.000%)" == result
    with get_connection_cm(auto=False) as connection:
        row = connection.execute("SELECT instance_date, logged_at FROM qada_logs").fetchone()
    assert tuple(row) == (jdatetime.date.today().strftime("%Y-%m-%d"), 456)


def test_fasting_log_supports_unbounded_target(qada_entry):
    entry = qada_entry(name="Fasting", kind="fasting", target_total=-1)
    assert "1/∞ (∞)" in logging.log_fasting(entry["id"])


def test_fasting_log_rejects_duplicate_and_zero_target(qada_entry):
    entry = qada_entry(name="Fasting", kind="fasting", target_total=1)
    logging.log_fasting(entry["id"])
    assert "Already logged" in logging.log_fasting(entry["id"])
    zero = qada_entry(name="Zero", kind="fasting", target_total=0)
    assert logging.log_fasting(zero["id"]) == "Target is 0. Nothing to log."


def test_pause_fasting_entry_handles_presence_and_absence(db_path, qada_entry):
    assert logging.pause_fasting_entry() == "No fasting entry found."
    qada_entry(name="Fasting", kind="fasting")
    assert "Paused Fasting" in logging.pause_fasting_entry()
