import jdatetime

from dailydriver.features.calendar.reminders import get_event_reminders, get_tomorrow_preview


def event(identifier, title, *, calendar="jalali", holiday=False):
    return {
        "id": identifier,
        "title_en": title,
        "calendar": calendar,
        "holiday": holiday,
    }


def test_reminders_follow_configured_schedule(db_connection):
    today = jdatetime.date(1405, 6, 1)
    db_connection.executemany(
        "INSERT INTO event_reminders (event_id, level) VALUES (?,?)",
        [(1, 1), (2, 1), (3, 0)],
    )
    events = [
        (today, event(1, "Today")),
        (today + jdatetime.timedelta(days=5), event(2, "Off schedule")),
        (today, event(3, "Disabled")),
    ]
    assert get_event_reminders(db_connection, events, today) == [("🔔🔆 ", "Today (today)")]


def test_reminder_labels_tomorrow_and_future(db_connection):
    today = jdatetime.date(1405, 6, 1)
    db_connection.executemany(
        "INSERT INTO event_reminders (event_id, level) VALUES (?,1)",
        [(1,), (2,)],
    )
    lines = get_event_reminders(
        db_connection,
        [
            (today + jdatetime.timedelta(days=1), event(1, "Tomorrow")),
            (today + jdatetime.timedelta(days=7), event(2, "Week")),
        ],
        today,
    )
    assert [title for _, title in lines] == ["Tomorrow tomorrow", "Week in 7 days"]


def test_holiday_prefix_alignment(db_connection):
    today = jdatetime.date(1405, 6, 1)
    db_connection.executemany(
        "INSERT INTO event_reminders (event_id, level) VALUES (?,1)",
        [(1,), (2,)],
    )
    lines = get_event_reminders(
        db_connection,
        [(today, event(1, "Holiday", holiday=True)), (today, event(2, "Normal"))],
        today,
    )
    assert "🎊" in lines[0][0]
    assert "  " in lines[1][0]


def test_tomorrow_preview_excludes_already_reminded_events():
    today = jdatetime.date(1405, 6, 1)
    tomorrow = today + jdatetime.timedelta(days=1)
    lines = get_tomorrow_preview(
        [(tomorrow, event(1, "Reminded")), (tomorrow, event(2, "Visible"))],
        today,
        reminded_ids={1},
    )
    assert lines == ["📅 Tomorrow:", ("🔆 ", "Visible")]


def test_tomorrow_preview_is_empty_without_visible_events():
    today = jdatetime.date(1405, 6, 1)
    tomorrow = today + jdatetime.timedelta(days=1)
    assert get_tomorrow_preview([], today) == []
    assert get_tomorrow_preview([(tomorrow, event(1, "Hidden"))], today, {1}) == []
