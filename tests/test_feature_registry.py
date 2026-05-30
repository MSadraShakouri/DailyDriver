import pkgutil

import dailydriver.features as features_pkg


def test_all_feature_packages_are_enabled():
    """Every subpackage in features/ must be in ENABLED, or explicitly excluded."""
    on_disk = {
        name for _, name, ispkg in pkgutil.iter_modules(features_pkg.__path__) if ispkg
    }
    enabled_names = {f.__name__.rsplit(".", 1)[-1] for f in features_pkg.ENABLED}
    missing = on_disk - enabled_names
    assert not missing, f"Feature packages on disk but not in ENABLED: {missing}"
