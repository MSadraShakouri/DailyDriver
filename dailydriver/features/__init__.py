# dailydriver/features/__init__.py
"""
Feature‑package registry.

Each feature lives in its own sub‑package and may expose any of the following
optional hooks (duck‑typed – no base class required):

    NAME: str – human‑readable feature name.
    VERSION: str – semantic version string (e.g., "1.0.0").

    def migrations() -> list[callable]:
        ...

    def register_commands(dispatch: dict) -> None:
        ...

    def header_sections() -> list[tuple[int, str]] | list[str]:
        ...

    def stats_sections() -> dict | None:
        ...

    def register_aliases(dispatch: dict) -> None:
        ...

Features are loaded in the order they appear in ENABLED.
"""

ENABLED = []