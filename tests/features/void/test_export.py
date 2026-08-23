import time

import pytest

from dailydriver.core.database import get_connection_cm
from dailydriver.features.void.export import _parse_duration, export_void


@pytest.mark.parametrize(
    ("value", "days"),
    [("all", 0), ("7d", 7), ("2w", 14), ("3m", 90), ("1y", 365), ("5", 5), ("bad", None)],
)
def test_duration_parser(value, days):
    assert _parse_duration(value) == days


def test_export_validates_arguments(db_path, ui):
    assert export_void("vexport") is None
    assert "Usage" in ui.lines[-1]
    assert export_void("vexport forever") is None
    assert "Invalid duration" in ui.lines[-1]


def test_export_reports_empty_range(db_path):
    assert export_void("vexport 7d") == "No void entries in the selected range."


def test_export_writes_grouped_markdown(db_path, tmp_path, monkeypatch):
    now = int(time.time())
    with get_connection_cm(auto=False) as connection:
        connection.executemany(
            "INSERT INTO void_entries (created_at, description) VALUES (?,?)",
            [(now - 60, "first"), (now, "second")],
        )
        connection.commit()
    monkeypatch.chdir(tmp_path)
    assert export_void("vexport all") == "Exported void entries to export_void_all.md (Markdown)"
    content = (tmp_path / "export_void_all.md").read_text()
    assert "# Void Export (all time)" in content
    assert "**Void**" in content
    assert "> first" in content
    assert "> second" in content
