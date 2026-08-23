"""Progress logging and aggregate history use real database boundaries."""

from dailydriver.features.targets import entries, history, progress


def test_finite_progress_is_capped_at_target(target, today):
    entry = target(target_total=10)
    assert "10/10" in progress.log_progress(entry["name"], 50)
    assert progress.log_progress(entry["name"], 1) == "Already at target. Nothing to log."
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 10


def test_indefinite_progress_accumulates(target, today):
    entry = target(name="Reading", kind="habit", target_total=None)
    assert progress.log_progress("Reading", 3) == "Reading: 3/∞"
    assert progress.log_progress("Reading", 2) == "Reading: 5/∞"
    assert entries.get_entry_by_id(entry["id"])["logged_total"] == 5


def test_progress_rejects_non_positive_missing_and_wrong_kind(target, today):
    target()
    assert progress.log_progress("Salavat", 0) == "Amount must be positive."
    assert progress.log_progress("Missing", 1) == "Entry not found: Missing"
    assert "not a habit" in progress.log_progress("Salavat", 1, expected_kind="habit")


def test_daily_total_sums_multiple_logs(target, today):
    entry = target()
    progress.log_progress(entry["name"], 3)
    progress.log_progress(entry["name"], 4)
    assert history.get_daily_total(entry["id"], today) == 7


def test_history_helpers_accept_existing_connection(target, today, db_connection):
    entry = target()
    progress.log_progress(entry["name"], 10)
    assert history.get_daily_total(entry["id"], today, conn=db_connection) == 10
    assert history.get_last_fulfilled_date(entry["id"], conn=db_connection) == today


def test_last_fulfilled_date_requires_interval_goal(target, today):
    entry = target(target_per_interval=10)
    progress.log_progress(entry["name"], 9)
    assert history.get_last_fulfilled_date(entry["id"]) is None
    progress.log_progress(entry["name"], 1)
    assert history.get_last_fulfilled_date(entry["id"]) == today


def test_any_positive_log_fulfils_entry_without_interval_goal(target, today):
    entry = target(target_per_interval=None)
    progress.log_progress(entry["name"], 1)
    assert history.get_last_fulfilled_date(entry["id"]) == today


def test_counter_defaults_updates_and_supports_connection(target, db_connection):
    entry = target()
    assert history.get_counter_value(entry["id"]) == 0
    history.set_counter_value(entry["id"], 42, conn=db_connection)
    assert history.get_counter_value(entry["id"], conn=db_connection) == 42
    assert history.get_counter_value(404) == 0
