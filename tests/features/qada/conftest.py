import pytest

from dailydriver.features.qada import entries


@pytest.fixture
def qada_entry(db_path):
    def create(
        name="Fajr",
        *,
        kind="prayer",
        slot="fajr",
        target_total=10,
        interval_type="daily",
        interval_value=None,
    ):
        entry_id = entries.add_entry(
            name=name,
            kind=kind,
            slot=slot if kind == "prayer" else None,
            target_total=target_total,
            interval_type=interval_type,
            interval_value=interval_value,
        )
        return entries.get_entry(entry_id)

    return create
