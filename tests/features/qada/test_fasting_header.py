import jdatetime

from dailydriver.features.qada import header

ENTRY = {
    "id": 1,
    "kind": "fasting",
    "slot": None,
    "interval_type": "daily",
    "target_total": 2,
    "logged_total": 0,
    "paused_until": None,
}


def test_fasting_nudges_only_apply_to_today(db_connection):
    tomorrow = jdatetime.date.today() + jdatetime.timedelta(days=1)
    assert header.get_fasting_nudges(db_connection, tomorrow) == []


def test_pending_overdue_and_unset_labels(db_connection, monkeypatch):
    today = jdatetime.date.today()
    monkeypatch.setattr(header, "list_entries", lambda kind: [ENTRY])
    monkeypatch.setattr(header, "compute_pending_instance", lambda entry, date: today)
    assert header.get_fasting_nudges(db_connection, today) == ["🌙 Fasting pending"]

    monkeypatch.setattr(
        header,
        "compute_pending_instance",
        lambda entry, date: today - jdatetime.timedelta(days=1),
    )
    assert header.get_fasting_nudges(db_connection, today) == ["🌙 Fasting overdue!"]

    monkeypatch.setattr(header, "list_entries", lambda kind: [ENTRY | {"target_total": -1}])
    monkeypatch.setattr(header, "compute_pending_instance", lambda entry, date: today)
    assert header.get_fasting_nudges(db_connection, today) == ["🌙 Fasting: not set"]


def test_paused_complete_and_unscheduled_entries_are_hidden(db_connection, monkeypatch):
    today = jdatetime.date.today()
    monkeypatch.setattr(
        header,
        "list_entries",
        lambda kind: [
            ENTRY | {"paused_until": today.strftime("%Y-%m-%d")},
            ENTRY | {"target_total": 1, "logged_total": 1},
            ENTRY | {"interval_type": None},
        ],
    )
    monkeypatch.setattr(header, "compute_pending_instance", lambda entry, date: today)
    assert header.get_fasting_nudges(db_connection, today) == []


def test_existing_log_hides_today_nudge(db_connection, monkeypatch):
    today = jdatetime.date.today()
    monkeypatch.setattr(header, "list_entries", lambda kind: [ENTRY])
    monkeypatch.setattr(header, "compute_pending_instance", lambda entry, date: today)
    db_connection.execute(
        "INSERT INTO qada_entries (id, name, kind, interval_type) VALUES (1, 'Fasting', 'fasting', 'daily')"
    )
    db_connection.execute(
        "INSERT INTO qada_logs (entry_id, amount, instance_date) VALUES (1, 1, ?)",
        (today.strftime("%Y-%m-%d"),),
    )
    db_connection.commit()
    assert header.get_fasting_nudges(db_connection, today) == []
