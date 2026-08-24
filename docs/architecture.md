# Architecture

DailyDriver is a small, modular Python application built around a
**feature-package** model: each domain (prayer, sleep, targets, …) is a
self-contained package that plugs into the app through a handful of optional
hooks.

## Package layout

```text
dailydriver/
├── core/       # database, migrations, journal persistence, shared state
├── features/   # enabled domain packages and their package-level hooks
├── display/    # header orchestration, rendering, and statistics
├── cli/        # REPL, dispatcher, help, and non-feature commands
├── ui/         # terminal abstraction (current_ui) and input backends
└── utils/      # domain-neutral parsing, dates, times, and intervals
data/           # database, stopwords, event JSON, hijri offset, history
tools/          # standalone HTML/Python editors and analysis scripts
tests/          # test tree mirroring dailydriver/
```

Dependency direction:

- `core/` does not depend on `cli/` or display code.
- `utils/` holds domain-neutral helpers and does not depend on features.
- Features may use `core/`, `utils/`, `ui/`, and display helpers.
- `cli/` and `display/` discover feature capabilities through the hooks.
- Cross-feature calls go through a deliberately named module/export, never a
  generic private module.

Events & chaining (`se`/`ee`/`ce`, `ln`, great events) are deliberately **not**
a feature package: state lives in `core/state/events.py`, commands in
`cli/commands/events.py`, and the header status lines are injected into the
priority-ordered stream by `display/header/events.py`.

## The feature contract

Each feature package's `__init__.py` is a thin adapter exposing metadata and
whichever hooks it needs:

```python
NAME = "prayer"        # stable, unique identifier
VERSION = "1.0.0"      # human-facing feature API version

def register_commands(dispatch): ...        # add command names + aliases
def header_sections(conn, today, target_date, is_today): ...  # header content
def migrations(): ...                        # ordered schema migrations
def export_items(conn, start, end=None): ...  # timeline items for `export`/`day`
```

Hooks are duck-typed and all optional; the registry validates metadata and hook
callability at startup, and rejects duplicate `NAME`s. Features are enabled
explicitly in `dailydriver/features/__init__.py`, whose order controls command
registration (header order is controlled only by numeric priorities).

The authoritative, detailed contract — including the exact shape of header
lines, migration rules, and export items — lives in
[`dailydriver/features/HOOKS.md`](../dailydriver/features/HOOKS.md).

## Input / UI backends

Input is abstracted behind `UI` (`dailydriver/ui/terminal_ui.py`) and the
`current_ui` singleton. Two backends exist:

- **`TerminalUI`** — plain `input()`/`print()`.
- **`PromptToolkitUI`** — adds command autocompletion, persistent history, and
  an autocompleting, ranked category picker.

`select_ui()` picks the prompt_toolkit backend on interactive terminals and
falls back to `TerminalUI` when prompt_toolkit is unavailable or stdin/stdout is
not a TTY. Only *input* is enriched; output is always plain text. Because both
backends share the `UI` interface, tests swap in a recorder without caring which
backend is live.

## Commands, dispatch, and help

`cli/dispatcher.py` builds a flat `dispatch: dict[str, handler]` from the core
commands plus every feature's `register_commands`. Handlers receive the full
command line and may return a string for the REPL to print.

Both the REPL (`repl()`) and the single-shot path (`run_single_command()`) route
through one `_dispatch_line()` in `cli/commander.py`, which:

1. intercepts `-h`/`--help` (matched as exact tokens, so `p -15` is unaffected)
   and renders per-command help;
2. otherwise calls the handler, or logs the line as a journal entry.

Command help is defined once in `cli/help_registry.py` (the single source of
truth); both `-h`/`--help` and the `?`/`h` summary read from it, so they can't
drift apart. A test guards that every registered command has a help entry.

## Data model & migrations

State is a single SQLite database at `data/daily.db` (override with
`DAILYDRIVER_DB`). Core tables include `categories`, `keywords`, `entries`,
`entry_categories`, prayer/sleep logs, a key/value `meta` table, and an FTS
index (kept in sync on writes; `search` itself is a token filter, not
FTS-ranked). Each feature owns its own tables and its own ordered migration
sequence; per-feature migration progress is tracked in `feature_versions`.
Released migrations are append-only — never reorder or remove one, since progress
is tracked by list position.

## Tools

`tools/` contains standalone helpers that are not part of the REPL: HTML/Python
editors for events, keywords, and reminders, plus analysis scripts like
`sleep_avg.py`. They operate directly on the database or data files.

See [CONTRIBUTING](../CONTRIBUTING.md) for workflow, style, and testing
conventions.
