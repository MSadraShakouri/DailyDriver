import pkgutil
from types import ModuleType

import pytest

import dailydriver.features as features_pkg
from dailydriver.features.registry import (
    FeatureContractError,
    optional_hook,
    validate_feature,
    validate_header_sections,
)


def _feature(name="example"):
    feature = ModuleType(name)
    feature.NAME = name
    feature.VERSION = "1.0.0"
    return feature


def test_all_feature_packages_are_enabled():
    """Every subpackage in features/ must be in ENABLED, or explicitly excluded."""
    on_disk = {name for _, name, ispkg in pkgutil.iter_modules(features_pkg.__path__) if ispkg}
    enabled_names = {feature.__name__.rsplit(".", 1)[-1] for feature in features_pkg.ENABLED}
    assert not on_disk - enabled_names


def test_internal_file_layout_is_not_part_of_contract():
    """Metadata-only features are valid; no `_logic.py`-style module is required."""
    feature = _feature()
    assert validate_feature(feature) is feature
    assert optional_hook(feature, "register_commands") is None


def test_present_hook_must_be_callable():
    feature = _feature()
    feature.header_sections = []
    with pytest.raises(FeatureContractError, match="must be callable"):
        validate_feature(feature)


def test_header_sections_have_one_explicit_ordering_representation():
    feature = _feature()
    assert validate_header_sections(feature, [(20, "weather")]) == [(20, "weather")]
    with pytest.raises(FeatureContractError, match=r"\(int priority, str text\)"):
        validate_header_sections(feature, ["implicitly first"])
