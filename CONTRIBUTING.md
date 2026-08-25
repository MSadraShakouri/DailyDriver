# Contributing

Thanks for your interest in DailyDriver.

User-facing and design documentation lives in [`docs/`](docs/); the
[architecture guide](docs/src/content/docs/architecture.md) expands on the
summary below.

## Package layout

```text
dailydriver/
├── core/           # database, migrations, journal persistence, shared state
├── features/       # enabled domain packages and their package-level hooks
├── display/        # header orchestration, rendering, and statistics
├── cli/            # REPL, dispatcher, and non-feature commands
├── ui/             # terminal abstraction (`current_ui`)
└── utils/          # domain-neutral parsing, dates, times, and intervals
```

Dependency direction should normally be:

- `core/` does not depend on `cli/` or display code;
- `utils/` contains domain-neutral helpers and does not depend on features;
- feature implementations may use `core/`, `utils/`, `ui/`, and display helpers;
- `cli/` and `display/` discover feature capabilities through the feature
  package hooks;
- cross-feature calls use a deliberately named module or package export, never
  a generic private `_logic` module.

## Adding a feature

Each feature is a package under `dailydriver/features/`. Its `__init__.py` is a
small adapter exposing `NAME`, `VERSION`, and whichever optional hooks it needs:

- `register_commands(dispatch)`;
- `header_sections(conn, today, target_date, is_today)`;
- `migrations()`.

Add the package to `dailydriver/features/__init__.py`. The registry validates
metadata and hooks at startup, and `tests/features/test_registry.py` catches
unregistered packages.

Only the package-level hook contract is enforced. **No internal filename such
as `_logic.py` is required.** Prefer modules named for responsibilities or
domain concepts, for example `commands.py`, `entries.py`, `schedule.py`,
`header.py`, and `migrations.py`. Small features should stay small; large
features should separate persistence, calculations, terminal UI, and command
parsing.

See [`dailydriver/features/HOOKS.md`](dailydriver/features/HOOKS.md) for the
complete runtime contract.

## Adding a command

Feature-owned commands belong in the feature package and are registered by its
`register_commands` hook. Primary names and aliases are registered together.

A genuinely application-wide command may live under `dailydriver/cli/commands/`
and be added to `make_dispatch()`. If it needs the unparsed command line, make
sure both the REPL and single-command path pass it through consistently.

## Style

- Follow the existing module docstrings and function naming.
- Keep package adapters declarative and free of import-time side effects.
- Keep functions focused; extract shared, domain-neutral behavior rather than
  copying it between feature managers.
- Use `current_ui.print_line()` and `current_ui.prompt()` for terminal I/O.
- Use `get_connection_cm()` for database ownership and close connections
  predictably.
- Keep lines at or below 120 characters where practical.

## Tests

Install the test extra, then run the suite and configured coverage check:

```bash
python -m pip install -e '.[test]'
python -m pytest
coverage run -m pytest
coverage report
```

The test tree mirrors `dailydriver/`; feature tests belong under
`tests/features/<feature>/`. Database use is opt-in through `db_path` or
`db_connection`, while interactive tests use the shared `ui` recorder. See
[`tests/README.md`](tests/README.md) for the full conventions.

During a feature refactor, run that feature's focused tests after each module
move or extraction, then run the complete suite before submitting.

## Pull requests

1. Fork the repository and create a branch.
2. Make focused changes and test thoroughly.
3. Open a pull request with a clear description of behavior and architecture
   changes.

For major behavior changes, please open an issue first to discuss the design.
