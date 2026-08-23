# Feature package contract

A DailyDriver feature is an enabled Python **package** under
`dailydriver/features/`. The package is the extension boundary; its internal
file names and classes are not part of the feature system.

The registry uses capability-based duck typing. A feature provides only the
hooks it needs, and the application asks for each capability with
`features.registry.optional_hook()`.

## Required package metadata

Every enabled feature package exposes:

```python
NAME = "weather"       # stable database/diagnostic identifier
VERSION = "1.0.0"      # feature API version for humans and tooling
```

`NAME` must be unique among enabled features. Both values must be non-empty
strings. `VERSION` does not determine schema migration progress; migration
position is stored separately in `feature_versions`.

## Optional hooks

### `register_commands(dispatch) -> None`

Register primary command names and aliases in the supplied command dictionary.
Handlers receive the complete command line and may return a string for the REPL
to print.

```python
def register_commands(dispatch):
    dispatch["p"] = commands.log_prayer
    dispatch["pray"] = commands.log_prayer
```

Aliases are commands too, so there is no separate alias hook.

### `header_sections(conn, today, target_date, is_today) -> sequence[(int, str)]`

Return zero or more `(priority, text)` items:

- `conn`: the header builder's open SQLite connection;
- `today`: displayed Jalali date as `YYYY-MM-DD`;
- `target_date`: displayed `jdatetime.date`;
- `is_today`: whether the current day is being displayed.

Lower priorities render first. Returning plain strings is not supported because
it creates a second, implicit ordering system.

```python
def header_sections(conn, today, target_date, is_today):
    line = header.weather_line(conn, today, is_today)
    return [(20, line)] if line else []
```

Header hooks should use the supplied connection for header-specific queries.
They must not commit unrelated changes. A feature that intentionally performs
maintenance while building the header should make that behavior explicit in a
named service function.

### `migrations() -> sequence[callable]`

Return all schema migrations for the feature in permanent chronological order.
Each migration receives an open SQLite connection. Never reorder or remove a
released migration: progress is tracked by list position.

Features without feature-owned schema do not define this hook.

## Internal organization

No internal module is required—not `_logic.py`, `_header.py`, or any other
filename. Organize implementation by responsibility and domain vocabulary:

```text
prayer/
├── __init__.py       # metadata and hooks (the feature adapter)
├── commands.py       # command handlers and parsing
├── schedule.py       # prayer-slot calculations
├── backlog.py        # missed-prayer workflow
└── header.py         # header presentation
```

Small features may need only `__init__.py` and one implementation module. Large
features should split persistence, domain calculations, commands, and terminal
UI instead of accumulating a generic `logic.py`.

Modules prefixed with `_` are not required or discovered specially. Existing
code should import another feature's explicitly named module or package export,
not depend on a generic private `_logic` module.

## Import and dependency rules

- Importing a feature package must not open the database, prompt, print, fetch
  from the network, or run migrations.
- `__init__.py` adapts implementation functions to hooks; it should contain
  little domain logic.
- Feature modules may depend on `core`, `ui`, and `utils`.
- Features may call another feature's deliberately exposed domain service, but
  circular feature imports are forbidden.
- Shared, domain-neutral behavior belongs in `dailydriver/utils/`. Shared
  feature-presentation helpers belong in `dailydriver/features/presentation.py`.
- Command aliases are registered together with primary commands.

## Enabling and ordering

Features are imported and listed explicitly in `dailydriver/features/__init__.py`.
The registry validates metadata and hook callability at startup. Explicit
registration keeps startup predictable and makes accidental feature packages
visible in tests.

Feature order controls command registration. Header order is controlled only by
numeric priorities. A later feature currently replaces an earlier command with
the same key, so command names should be treated as globally unique.

## What is deliberately not a hook

- `stats_sections` is not part of the contract because the current statistics
  command does not consume it.
- `register_aliases` is unnecessary; aliases are ordinary commands.
- Internal file names and base classes are not extension points.
