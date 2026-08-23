from datetime import datetime

import jdatetime
import pytest

from dailydriver.core import day_start


def test_default_and_persisted_day_start(db_path):
    assert day_start.get_day_start_hour() == 4
    day_start.set_day_start_hour(6)
    assert day_start.get_day_start_hour() == 6


@pytest.mark.parametrize("hour", [-1, 24])
def test_invalid_day_start_is_rejected(db_path, hour):
    with pytest.raises(ValueError, match="between 0 and 23"):
        day_start.set_day_start_hour(hour)


def test_malformed_stored_value_falls_back_to_default(db_connection):
    db_connection.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('day_start_hour', 'bad')")
    db_connection.commit()
    assert day_start.get_day_start_hour() == 4


def test_shifted_today_moves_pre_boundary_time_to_previous_date(db_path):
    day_start.set_day_start_hour(4)
    before = datetime(2026, 8, 23, 3, 59)
    after = datetime(2026, 8, 23, 4, 0)
    expected = jdatetime.date.fromgregorian(date=before.date())
    assert day_start.get_shifted_today(before) == expected - jdatetime.timedelta(days=1)
    assert day_start.get_shifted_today(after) == expected


def test_timestamp_shift_uses_same_boundary(db_path):
    day_start.set_day_start_hour(4)
    before = datetime(2026, 8, 23, 3).timestamp()
    after = datetime(2026, 8, 23, 5).timestamp()
    date = jdatetime.date.fromgregorian(date=datetime(2026, 8, 23).date())
    assert day_start.shift_timestamp_to_date(before) == date - jdatetime.timedelta(days=1)
    assert day_start.shift_timestamp_to_date(after) == date
