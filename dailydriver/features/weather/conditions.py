"""Persistence and translation of IRIMO condition labels."""

import json
from pathlib import Path

TRANSLATION_FILE = Path(__file__).resolve().parents[3] / "data" / "weather_conditions.json"


def load_translations() -> dict:
    if not TRANSLATION_FILE.exists():
        return {}
    with TRANSLATION_FILE.open(encoding="utf-8") as file:
        return json.load(file)


def save_translations(translations: dict) -> None:
    with TRANSLATION_FILE.open("w", encoding="utf-8") as file:
        json.dump(translations, file, ensure_ascii=False, indent=2)


def translate_condition(condition_fa: str) -> dict | None:
    """Return English/emoji metadata, recording unknown labels for translation."""
    translations = load_translations()
    if condition_fa not in translations:
        translations[condition_fa] = {"en": "NOT TRANSLATED", "emoji": "❓"}
        save_translations(translations)
        return None
    entry = translations[condition_fa]
    return None if entry["en"] == "NOT TRANSLATED" else entry
