"""Runtime contract for pluggable DailyDriver features.

A feature is a package listed in :data:`dailydriver.features.ENABLED`.  The
registry deliberately knows nothing about files inside that package; it only
looks for the optional hooks defined here.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from types import ModuleType
from typing import Any, TypeAlias, TypeVar, cast

HeaderLine: TypeAlias = str | tuple[str, str]
HeaderSection: TypeAlias = tuple[int, HeaderLine]
Migration: TypeAlias = Callable[[Any], None]
CommandHandler: TypeAlias = Callable[[str], Any]
CommandMap: TypeAlias = dict[str, CommandHandler]
ExportItem: TypeAlias = dict[str, Any]

Hook = TypeVar("Hook", bound=Callable[..., Any])
_HOOK_NAMES = ("register_commands", "header_sections", "migrations", "export_items")


class FeatureContractError(TypeError):
    """Raised when an enabled package does not satisfy the feature contract."""



def optional_hook(feature: ModuleType, name: str) -> Callable[..., Any] | None:
    """Return a callable hook from *feature*, or ``None`` when it is absent.

    Present-but-non-callable hooks are configuration errors rather than absent
    capabilities.  This keeps feature discovery duck-typed while failing early
    on misspellings and incomplete refactors.
    """
    hook = getattr(feature, name, None)
    if hook is None:
        return None
    if not callable(hook):
        raise FeatureContractError(f"{feature.__name__}.{name} must be callable")
    return hook



def validate_feature(feature: ModuleType) -> ModuleType:
    """Validate package-level metadata and any hooks a feature exposes."""
    name = getattr(feature, "NAME", None)
    version = getattr(feature, "VERSION", None)
    if not isinstance(name, str) or not name.strip():
        raise FeatureContractError(f"{feature.__name__}.NAME must be a non-empty string")
    if not isinstance(version, str) or not version.strip():
        raise FeatureContractError(f"{feature.__name__}.VERSION must be a non-empty string")
    for hook_name in _HOOK_NAMES:
        optional_hook(feature, hook_name)
    return feature



def validate_features(features: Iterable[ModuleType]) -> tuple[ModuleType, ...]:
    """Validate enabled features and reject duplicate stable names."""
    validated = tuple(validate_feature(feature) for feature in features)
    names = [feature.NAME for feature in validated]
    duplicates = sorted({name for name in names if names.count(name) > 1})
    if duplicates:
        raise FeatureContractError(f"duplicate feature NAME values: {', '.join(duplicates)}")
    return validated



def command_hook(feature: ModuleType) -> Callable[[CommandMap], None] | None:
    """Return the feature's command registration hook, if provided."""
    return cast(Callable[[CommandMap], None] | None, optional_hook(feature, "register_commands"))



def header_hook(feature: ModuleType) -> Callable[..., Sequence[HeaderSection]] | None:
    """Return the feature's header hook, if provided."""
    return cast(Callable[..., Sequence[HeaderSection]] | None, optional_hook(feature, "header_sections"))



def migration_hook(feature: ModuleType) -> Callable[[], Sequence[Migration]] | None:
    """Return the feature's migration hook, if provided."""
    return cast(Callable[[], Sequence[Migration]] | None, optional_hook(feature, "migrations"))



def export_hook(feature: ModuleType) -> Callable[..., Sequence[ExportItem]] | None:
    """Return the feature's unified-export hook, if provided."""
    return cast(Callable[..., Sequence[ExportItem]] | None, optional_hook(feature, "export_items"))



def validate_header_sections(feature: ModuleType, sections: object) -> list[HeaderSection]:
    """Validate and normalize the value returned by ``header_sections``."""
    if sections is None:
        return []
    if isinstance(sections, (str, bytes)) or not isinstance(sections, Sequence):
        raise FeatureContractError(f"{feature.__name__}.header_sections must return a sequence")

    normalized: list[HeaderSection] = []
    for section in sections:
        if not isinstance(section, tuple) or len(section) != 2 or not isinstance(section[0], int):
            raise FeatureContractError(
                f"{feature.__name__}.header_sections entries must be (int priority, header line) tuples"
            )

        line = section[1]
        structured_line = (
            isinstance(line, tuple) and len(line) == 2 and isinstance(line[0], str) and isinstance(line[1], str)
        )
        if not isinstance(line, str) and not structured_line:
            raise FeatureContractError(
                f"{feature.__name__}.header_sections content must be text or a (prefix, title) tuple"
            )
        normalized.append(cast(HeaderSection, section))
    return normalized



def validate_migrations(feature: ModuleType, migrations: object) -> list[Migration]:
    """Validate and normalize migrations returned by a feature hook."""
    if isinstance(migrations, (str, bytes)) or not isinstance(migrations, Sequence):
        raise FeatureContractError(f"{feature.__name__}.migrations must return a sequence")
    result = list(migrations)
    if not all(callable(migration) for migration in result):
        raise FeatureContractError(f"{feature.__name__}.migrations entries must be callable")
    return result
