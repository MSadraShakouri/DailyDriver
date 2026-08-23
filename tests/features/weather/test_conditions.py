import json

from dailydriver.features.weather import conditions


def test_missing_translation_file_is_empty(tmp_path, monkeypatch):
    monkeypatch.setattr(conditions, "TRANSLATION_FILE", tmp_path / "conditions.json")
    assert conditions.load_translations() == {}


def test_unknown_condition_is_recorded_for_translation(tmp_path, monkeypatch):
    path = tmp_path / "conditions.json"
    monkeypatch.setattr(conditions, "TRANSLATION_FILE", path)
    assert conditions.translate_condition("ناشناخته") is None
    assert json.loads(path.read_text())["ناشناخته"] == {"en": "NOT TRANSLATED", "emoji": "❓"}


def test_known_translation_is_returned(tmp_path, monkeypatch):
    path = tmp_path / "conditions.json"
    path.write_text(json.dumps({"صاف": {"en": "clear", "emoji": "☀️"}}))
    monkeypatch.setattr(conditions, "TRANSLATION_FILE", path)
    assert conditions.translate_condition("صاف") == {"en": "clear", "emoji": "☀️"}
