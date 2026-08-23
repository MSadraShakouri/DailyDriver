import jdatetime

from dailydriver.features.qada import entries, logging, overview


def test_overview_creates_four_canonical_entries(db_path):
    rows = overview.get_all_entries_with_progress()
    assert [row["name"] for row in rows] == ["Fajr", "Dhuhr/Asr", "Maghrib/Isha", "Fasting"]
    assert all(row["progress_display"] == "Not set" for row in rows)
    assert len(entries.list_entries()) == 4


def test_overview_reports_progress_completion_and_percentage(db_path):
    row = overview.get_all_entries_with_progress()[0]
    entries.edit_entry(row["id"], target_total=4)
    logging.log_prayer_qada(row["id"], 2)
    current = overview.get_all_entries_with_progress()[0]
    assert current["progress_display"] == "2/4"
    assert current["percentage"] == 50
    assert not current["is_complete"]

    logging.log_prayer_qada(row["id"], 2)
    assert overview.get_all_entries_with_progress()[0]["is_complete"]


def test_overview_marks_zero_target_complete(db_path):
    row = overview.get_all_entries_with_progress()[0]
    entries.edit_entry(row["id"], target_total=0)
    current = overview.get_all_entries_with_progress()[0]
    assert current["progress_display"] == "0/0"
    assert current["is_complete"]


def test_overview_reports_paused_entry(db_path):
    today = jdatetime.date.today()
    row = overview.get_all_entries_with_progress()[0]
    entries.edit_entry(row["id"], target_total=10)
    entries.edit_entry(row["id"], paused_until=(today + jdatetime.timedelta(days=1)).strftime("%Y-%m-%d"))
    current = overview.get_all_entries_with_progress()[0]
    assert current["is_paused"]
    assert current["next_instance"] is None
