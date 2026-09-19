from datetime import date

import pytest

from tools.update_hijri_iran import build_payload, refresh


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
