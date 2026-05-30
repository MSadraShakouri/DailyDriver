import os

import pytest

from dailydriver.core.migration import run_migrations


@pytest.fixture(autouse=True, scope="session")
def isolated_db(monkeypatch, tmp_path_factory):
    """Redirect database to a temp file and run migrations once per session."""
    db_file = tmp_path_factory.mktemp("data") / "test.db"
    monkeypatch.setenv("DAILYDRIVER_DB", str(db_file))
    run_migrations()
    yield db_file
