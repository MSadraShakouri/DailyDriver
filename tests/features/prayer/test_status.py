from datetime import datetime

from dailydriver.features.prayer.status import get_prayer_parts


def test_empty_status_contains_three_placeholders(db_connection):
    assert get_prayer_parts(db_connection, "1405-06-01") == ["🌅  — ", "☀️  — ", "🌆  — "]


def test_status_uses_matching_date_and_slot(db_connection):
    timestamp = int(datetime(2026, 8, 23, 4, 42).timestamp())
    db_connection.execute(
        """INSERT INTO prayer_logs
           (prayer_slot, jalali_date, status, prayer_time)
           VALUES ('fajr', '1405-06-01', 'on_time', ?)""",
        (timestamp,),
    )
    db_connection.commit()
    assert "04:42" in get_prayer_parts(db_connection, "1405-06-01")[0]
    assert "04:42" not in "".join(get_prayer_parts(db_connection, "1405-06-02"))
