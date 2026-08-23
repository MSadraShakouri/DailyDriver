from dailydriver.features.calendar import catalog, hijri


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
