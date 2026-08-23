"""Shared test fixtures.

Database isolation is opt-in: pure unit tests should not pay for, or silently
depend on, a migrated database. Tests that need persistence request ``db_path``
or ``db_connection`` explicitly.
"""

from __future__ import annotations

import os
import shutil
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from dailydriver.core.database import get_connection
from dailydriver.core.migration import run_migrations
from dailydriver.ui.terminal_ui import current_ui


@pytest.fixture(scope="session")
def migrated_db_template(tmp_path_factory) -> Path:
    """Build one current-schema database that tests can cheaply copy."""
    path = tmp_path_factory.mktemp("database-template") / "daily.db"
    previous = os.environ.get("DAILYDRIVER_DB")
    os.environ["DAILYDRIVER_DB"] = str(path)
    try:
        run_migrations()
    finally:
        if previous is None:
            os.environ.pop("DAILYDRIVER_DB", None)
        else:
            os.environ["DAILYDRIVER_DB"] = previous
    return path


@pytest.fixture
def db_path(migrated_db_template, tmp_path, monkeypatch) -> Path:
    """Provide a fully migrated, test-local database through DAILYDRIVER_DB."""
    path = tmp_path / "daily.db"
    shutil.copy2(migrated_db_template, path)
    monkeypatch.setenv("DAILYDRIVER_DB", str(path))
    return path


# Transitional name retained for tests whose behavior explicitly concerns
# cross-connection persistence. New tests should request db_path.
@pytest.fixture
def isolated_db(db_path) -> Path:
    return db_path


@pytest.fixture
def db_connection(db_path):
    connection = get_connection(auto=False)
    try:
        yield connection
    finally:
        connection.close()


@pytest.fixture
def fresh_conn(db_path):
    """Track independent connections and close all of them after a test."""
    connections = []

    def factory():
        connection = get_connection(auto=False)
        connections.append(connection)
        return connection

    yield factory
    for connection in connections:
        connection.close()


@dataclass
class UIRecorder:
    """Deterministic terminal UI replacement used by interactive tests."""

    responses: deque[str] = field(default_factory=deque)
    lines: list[str] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)
    cleared: int = 0

    def queue(self, *responses: str) -> None:
        self.responses.extend(responses)

    def prompt(self, text: str = "") -> str:
        self.prompts.append(text)
        return self.responses.popleft() if self.responses else ""

    def print_line(self, text: str = "") -> None:
        self.lines.append(str(text))

    def clear(self) -> None:
        self.cleared += 1

    def confirm(self, *args, **kwargs) -> bool:
        return True


@pytest.fixture
def ui(monkeypatch) -> UIRecorder:
    """Patch the shared terminal singleton without replacing module imports."""
    recorder = UIRecorder()
    monkeypatch.setattr(current_ui, "prompt", recorder.prompt)
    monkeypatch.setattr(current_ui, "print_line", recorder.print_line)
    monkeypatch.setattr(current_ui, "clear", recorder.clear)
    monkeypatch.setattr(current_ui, "confirm", recorder.confirm)
    monkeypatch.setattr(current_ui, "confirm_time", recorder.confirm)
    return recorder
