import json
from datetime import date
from io import BytesIO
from urllib.error import HTTPError

import pytest

from tools.update_hijri_iran import OUTPUT_FILE, SOURCE_URL, build_payload, refresh

SOURCE = """
/*1264*/ 0b101010101010
/*1265*/ 0b010101010101
"""


def test_build_payload_decodes_packed_month_lengths_and_julian_start():
    payload = build_payload(SOURCE, source_url="test://iranian")

    assert payload["source"] == "test://iranian"
    assert payload["months"][0] == {
        "hijri": "1264-01",
        "start": "1847-12-09",
        "days": 30,
    }
    assert payload["months"][1]["days"] == 29
    assert payload["months"][-1]["hijri"] == "1265-12"


def test_refresh_fetches_the_current_multiplatform_source_by_default(monkeypatch, tmp_path):
    expected_url = (
        "https://raw.githubusercontent.com/persian-calendar/calendar/main/"
        "src/commonMain/kotlin/io/github/persiancalendar/calendar/islamic/"
        "IranianIslamicDateConverter.kt"
    )

    def fake_urlopen(request, *, timeout):
        assert request.full_url == expected_url
        assert request.get_header("User-agent") == "DailyDriver Hijri updater"
        assert timeout == 30
        return BytesIO(SOURCE.encode("utf-8"))

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    output = tmp_path / "hijri_iran.json"

    assert refresh(output=output, today=date(1847, 1, 1))
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["source"] == expected_url
    assert payload["months"] == build_payload(SOURCE)["months"]


def test_bundled_table_records_the_current_source_url():
    payload = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
    assert payload["source"] == SOURCE_URL


def test_refresh_preserves_existing_table_when_download_returns_404(monkeypatch, tmp_path):
    output = tmp_path / "hijri_iran.json"
    output.write_text("existing table\n", encoding="utf-8")

    def fake_urlopen(request, *, timeout):
        raise HTTPError(request.full_url, 404, "Not Found", None, None)

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    with pytest.raises(HTTPError) as error:
        refresh(output=output)

    assert error.value.code == 404
    assert output.read_text(encoding="utf-8") == "existing table\n"
    assert not output.with_suffix(".json.tmp").exists()


def test_refresh_is_atomic_and_does_not_rewrite_identical_data(tmp_path):
    source_file = tmp_path / "IranianIslamicDateConverter.kt"
    output = tmp_path / "hijri_iran.json"
    source_file.write_text(SOURCE)

    assert refresh(
        output=output,
        source_file=source_file,
        source_url="test://iranian",
        minimum_future_months=18,
        today=date(1847, 1, 1),
    )
    first = output.read_text()
    assert not output.with_suffix(".json.tmp").exists()
    assert not refresh(
        output=output,
        source_file=source_file,
        source_url="test://iranian",
        minimum_future_months=18,
        today=date(1847, 1, 1),
    )
    assert output.read_text() == first


def test_refresh_rejects_a_table_without_the_required_future_horizon(tmp_path):
    source_file = tmp_path / "IranianIslamicDateConverter.kt"
    source_file.write_text(SOURCE)

    with pytest.raises(RuntimeError, match="fewer than 18 future month starts"):
        refresh(
            output=tmp_path / "hijri_iran.json",
            source_file=source_file,
            minimum_future_months=18,
            today=date(2026, 1, 1),
        )
