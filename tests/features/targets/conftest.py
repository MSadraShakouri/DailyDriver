import jdatetime
import pytest

from dailydriver.features.targets import clock, entries


@pytest.fixture
def today(monkeypatch):
    value = jdatetime.date(1405, 6, 1)
    monkeypatch.setattr(clock, "today", lambda: value)
    return value


@pytest.fixture
def target(db_path):
    created = []

    def create(
        name="Salavat",
        *,
        kind="nazr",
        target_total=100,
        interval_type="daily",
        interval_value=1,
        target_per_interval=10,
    ):
        entry_id = entries.add_entry(
            kind=kind,
            name=name,
            target_total=target_total,
            interval_type=interval_type,
            interval_value=interval_value,
            target_per_interval=target_per_interval,
        )
        created.append(entry_id)
        return entries.get_entry_by_id(entry_id)

    return create
