from datetime import datetime

from dailydriver.features.sleep.status import get_nap_str, get_sleep_str


def _timestamp(hour, minute=0):
    return int(datetime(2026, 8, 22, hour, minute).timestamp())


def test_empty_sleep_and_nap_status(db_connection):
    assert get_sleep_str(db_connection, "1405-06-01") == "💤 —"
    assert get_nap_str(db_connection, "1405-06-01") == ""


def test_sleep_status_aggregates_ranges(db_connection):
    db_connection.executemany(
        "INSERT INTO sleep_logs (jalali_date, sleep_time, wake_time, duration_minutes) VALUES (?,?,?,?)",
        [
            ("1405-06-01", _timestamp(0), _timestamp(6), 360),
            ("1405-06-01", _timestamp(7), _timestamp(8), 60),
        ],
    )
    result = get_sleep_str(db_connection, "1405-06-01")
    assert "7h 0m" in result
    assert "00:00-06:00" in result
    assert "07:00-08:00" in result


def test_nap_status_aggregates_ranges(db_connection):
    db_connection.executemany(
        "INSERT INTO nap_logs (jalali_date, start_time, duration_minutes) VALUES (?,?,?)",
        [
            ("1405-06-01", _timestamp(13), 20),
            ("1405-06-01", _timestamp(15), 40),
        ],
    )
    result = get_nap_str(db_connection, "1405-06-01")
    assert "1h 0m" in result
    assert "13:00-13:20" in result
    assert "15:00-15:40" in result
