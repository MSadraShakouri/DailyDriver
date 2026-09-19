from datetime import date

from dailydriver.features.calendar import catalog, commands, hijri


def test_missing_and_corrupt_offset_default_to_zero(tmp_path, monkeypatch):
    path = tmp_path / "offset.txt"
    monkeypatch.setattr(hijri, "OFFSET_FILE", path)
    assert hijri.get_hijri_offset() == 0
    path.write_text("bad\n")
    assert hijri.get_hijri_offset() == 0


def test_offset_round_trip_records_date_and_invalidates_cache(tmp_path, monkeypatch):
    path = tmp_path / "offset.txt"
    monkeypatch.setattr(hijri, "OFFSET_FILE", path)
    catalog._cached_events = ["stale"]
    catalog._cache_year = 1405
    hijri.set_hijri_offset(-1)
    assert hijri.get_hijri_offset() == -1
    lines = path.read_text().splitlines()
    assert lines[0] == "-1"
    assert len(lines[1].split("-")) == 3
    assert catalog._cached_events is None
    assert catalog._cache_year is None


def test_month_override_takes_precedence_and_can_explicitly_select_zero(tmp_path, monkeypatch):
    offset_path = tmp_path / "offset.txt"
    offset_path.write_text("1\n2026-01-01\n")
    overrides_path = tmp_path / "overrides.json"
    monkeypatch.setattr(hijri, "OFFSET_FILE", offset_path)
    monkeypatch.setattr(hijri, "OVERRIDES_FILE", overrides_path)

    assert hijri.get_hijri_month_offset(1448, 4) == 1
    hijri.set_hijri_month_offset(1448, 4, 0)

    assert hijri.get_hijri_month_override(1448, 4) == 0
    assert hijri.get_hijri_month_offset(1448, 4) == 0
    assert hijri.get_hijri_month_offset(1448, 5) == 1
    assert '"1448-04"' in overrides_path.read_text()


def test_zero_is_not_written_when_legacy_global_offset_is_zero(tmp_path, monkeypatch):
    offset_path = tmp_path / "offset.txt"
    offset_path.write_text("0\n2026-01-01\n")
    overrides_path = tmp_path / "overrides.json"
    monkeypatch.setattr(hijri, "OFFSET_FILE", offset_path)
    monkeypatch.setattr(hijri, "OVERRIDES_FILE", overrides_path)

    hijri.set_hijri_month_offset(1448, 4, 0)

    assert not overrides_path.exists()


def test_zero_removes_an_unneeded_existing_month_override(tmp_path, monkeypatch):
    offset_path = tmp_path / "offset.txt"
    offset_path.write_text("0\n2026-01-01\n")
    overrides_path = tmp_path / "overrides.json"
    overrides_path.write_text(
        '{"schema_version": 1, "overrides": ' '{"1448-04": {"offset": -1, "set_date": "2026-01-01"}}}'
    )
    monkeypatch.setattr(hijri, "OFFSET_FILE", offset_path)
    monkeypatch.setattr(hijri, "OVERRIDES_FILE", overrides_path)

    hijri.set_hijri_month_offset(1448, 4, 0)

    assert hijri.get_hijri_month_override(1448, 4) is None


def test_command_saves_the_current_hijri_month_override(monkeypatch):
    class FixedDate(date):
        @classmethod
        def today(cls):
            return cls(2026, 9, 19)

    class FakeUI:
        def print_line(self, _line=""):
            pass

        def prompt(self, _message):
            return "-1"

    calls = []
    monkeypatch.setattr(commands, "date", FixedDate)
    monkeypatch.setattr(commands, "current_ui", FakeUI())
    monkeypatch.setattr(
        commands,
        "set_hijri_month_offset",
        lambda year, month, offset: calls.append((year, month, offset)),
    )

    commands._show_menu()

    assert calls == [(1448, 4, -1)]
