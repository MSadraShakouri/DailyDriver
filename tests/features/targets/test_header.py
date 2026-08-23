import jdatetime

from dailydriver.features.targets import entries, header, progress


def test_header_shows_due_goals_for_both_kinds(target, today, db_connection):
    target(name="Finite", kind="nazr", target_total=100, target_per_interval=10)
    target(name="Habit", kind="habit", target_total=None, target_per_interval=2)
    lines = header.get_targets_header_lines(db_connection)
    assert any("🎯 Finite: 0/10 for today" in line for line in lines)
    assert any("📊 Habit: 0/2 for today" in line for line in lines)


def test_header_hides_completed_paused_and_unscheduled_entries(target, today, db_connection):
    done = target(name="Done", target_per_interval=1)
    progress.log_progress(done["name"], 1)
    paused = target(name="Paused")
    entries.toggle_pause(paused["id"], 1)
    target(name="Unscheduled", interval_type=None, interval_value=None)
    assert header.get_targets_header_lines(db_connection) == []


def test_header_hook_only_runs_for_today(db_connection, monkeypatch):
    monkeypatch.setattr(header, "get_targets_header_lines", lambda connection: ["line"])
    date = jdatetime.date(1405, 6, 1)
    assert header.header_sections(db_connection, "1405-06-01", date, False) == []
    assert header.header_sections(db_connection, "1405-06-01", date, True) == [(31, "line")]
