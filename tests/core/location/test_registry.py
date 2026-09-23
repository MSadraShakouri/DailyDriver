import json

import pytest

from dailydriver.core.location import registry as registry_mod
from dailydriver.core.location.registry import RegistryError, get_city, load_registry


def test_shipped_registry_has_the_four_launch_cities():
    cities = load_registry()
    assert set(cities) == {"Tehran", "Karaj", "Qom", "Mashhad"}
    tehran = cities["Tehran"]
    assert tehran.name == "Tehran"
    assert tehran.lat == pytest.approx(35.689198)
    assert tehran.lon == pytest.approx(51.388974)
    assert tehran.tz == pytest.approx(3.5)
    # Every shipped city has an IRIMO weather page; Tehran's matches the
    # URL the weather provider has always used.
    for city in cities.values():
        assert city.weather_url and city.weather_url.startswith("http")
    from dailydriver.features.weather.provider import IRIMO_URL

    assert cities["Tehran"].weather_url == IRIMO_URL


def test_valid_minimal_entry_loads_without_weather_url(tmp_path):
    path = tmp_path / "cities.json"
    path.write_text(json.dumps({"Yazd": {"lat": 31.9, "lon": 54.37, "tz": 3.5}}), encoding="utf-8")
    cities = load_registry(str(path))
    assert cities["Yazd"].weather_url is None


def test_malformed_json_is_rejected(tmp_path):
    path = tmp_path / "cities.json"
    path.write_text("{not json", encoding="utf-8")
    with pytest.raises(RegistryError):
        load_registry(str(path))


def test_missing_file_is_rejected(tmp_path):
    with pytest.raises(RegistryError):
        load_registry(str(tmp_path / "absent.json"))


def test_malformed_entries_are_rejected(tmp_path):
    path = tmp_path / "cities.json"
    path.write_text(json.dumps({"Bad": {"lat": "north"}}), encoding="utf-8")
    with pytest.raises(RegistryError):
        load_registry(str(path))

    path.write_text(json.dumps(["Tehran"]), encoding="utf-8")
    with pytest.raises(RegistryError):
        load_registry(str(path))

    path.write_text(json.dumps({}), encoding="utf-8")
    with pytest.raises(RegistryError):
        load_registry(str(path))


def test_get_city_uses_the_default_registry(monkeypatch):
    monkeypatch.setattr(registry_mod, "REGISTRY_PATH", registry_mod.REGISTRY_PATH)
    assert get_city("Karaj") is not None
    assert get_city("Atlantis") is None
