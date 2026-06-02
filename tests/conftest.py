import os
import shutil

import pytest

from dailydriver.core.migration import run_migrations


@pytest.fixture(scope="session")
def _session_db_path(tmp_path_factory):
    """Create a fully-migrated database file once per session."""
    db_file = tmp_path_factory.mktemp("data") / "migrated.db"
    os.environ["DAILYDRIVER_DB"] = str(db_file)
    run_migrations()
    return db_file


@pytest.fixture(autouse=True)
def isolated_db(_session_db_path, tmp_path, monkeypatch):
    """Copy the session DB to a temp file for per-test isolation."""
    db_copy = tmp_path / "test.db"
    shutil.copy2(_session_db_path, db_copy)
    monkeypatch.setenv("DAILYDRIVER_DB", str(db_copy))
    yield db_copy
