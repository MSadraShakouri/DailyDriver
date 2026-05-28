import os

import pytest

from dailydriver.core.migration import run_migrations


@pytest.fixture(autouse=True)
def isolated_db(monkeypatch, tmp_path):
    """Redirect database to a temp file and run migrations before any test."""
    db_file = tmp_path / "test.db"
    monkeypatch.setenv("DAILYDRIVER_DB", str(db_file))
    run_migrations()
    yield db_file
