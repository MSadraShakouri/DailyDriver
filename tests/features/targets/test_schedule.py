import jdatetime

from dailydriver.features.targets import entries, progress, schedule


def test_no_interval_has_no_due_date(target, today):
    entry = target(interval_type=None, interval_value=None)
    assert schedule.compute_next_due(entry, today) is None


def test_paused_entry_has_no_due_date(target, today):
    entry = target()
    entries.toggle_pause(entry["id"], days=2)
    assert schedule.compute_next_due(entries.get_entry_by_id(entry["id"]), today) is None


def test_daily_entry_is_due_day_after_fulfilment(target, today):
    entry = target(target_per_interval=10)
    progress.log_progress(entry["name"], 10)
    updated = entries.get_entry_by_id(entry["id"])
    assert schedule.compute_next_due(updated, today) == today + jdatetime.timedelta(days=1)


def test_weekly_due_date_uses_requested_weekday(target, today):
    entry = target(interval_type="weekly", interval_value=0)
    due = schedule.compute_next_due(entry, today)
    assert due.weekday() == 0
    assert due >= today


def test_schedule_wrappers_expose_history(target, today):
    entry = target(target_per_interval=1)
    progress.log_progress(entry["name"], 1)
    assert schedule.get_daily_total_for_entry(entry["id"], today) == 1
    assert schedule.get_last_fulfilled_date_for_entry(entry["id"]) == today
