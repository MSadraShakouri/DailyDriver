# Reviewer Suggestions – Pending & Deferred

Captured from the external review (v1.4.0) and subsequent discussion.
Items we have already completed (dispatcher unification, test isolation, etc.)
are **not** listed here.

---

## 1. Code‑quality improvements

- **keyword_learner `find_matching_categories`**: issues N queries (one per token).  
  → batch into a single `WHERE word IN (?,?,…)` query.
- **IDF formula**: `math.log(total_cats / (df + 1))` can go negative. Clamp with `max(0.0, …)`.
- **EXACT_MATCH_BOOST**: substring match `token_lower in path.lower()` produces false positives
  (e.g., “art” matches “start”). Use word‑boundary regex or split the path on `/`.
- **`weather._fetch_failed_this_session`** module‑level mutable – move to a small class if ever
  multi‑threaded.
- **`log_free_text`** is 100+ lines with nested loops. Extract `_resolve_time(cmd)` and
  `_resolve_categories(cmd)` for readability and testability.
- **`time_parser.py`** (439 lines) – consider splitting into `tokens.py` / `interpretations.py` /
  `parser.py` if it keeps growing.
- **`tools/*.html` editors** – add a short section in the README explaining when to use them.
- **Missing `__main__.py`** – so `python -m dailydriver` works.
- **`time.time()` scattered everywhere** – inject a `clock()` callable or use `freezegun` in tests.
- **Repository has 0 stars / 0 forks** – add screenshots / asciinema cast of the header to README.

## 2. Architecture & design (medium‑term)

- **Service layer / Repository pattern** – would make CLI commands thinner and tests easier.
  Deferred until multiple frontends exist.
- **Replace `meta` table key/value pairs** with typed columns or a settings table.
  Deferred (current approach is fine for personal use).
- **`choose_from_list` UI method** – already defined in `terminal_ui.py` but under‑used.
  Replace scattered `print_line(f"  [{i}] {item}")` loops with calls to it.

## 3. User‑facing features (nice‑to‑have)

- **Undo command** – delete the last entry.
- **CSV export** – alongside existing Markdown / plain‑text export.
- **Tab completion** in the REPL – `readline` completer over `dispatch.keys()` (~10 lines).
- **Persistent command history** – `readline.read_history_file` / `write_history_file`.
- **Backup command** – copies `daily.db` to a timestamped backup folder.

## 4. Plugin / Feature‑Refactor Roadmap

We decided against building a full plugin system immediately, and instead to first reorganise
the code into “feature packages” (`dailydriver/features/…`). This document records the design
decisions and the steps we still need to take.

### 4.1 Hook design (agreed, not yet implemented)

Each feature package exposes **any** of the following optional hooks (duck typing, no ABC):

```python
# dailydriver/features/<name>/__init__.py

NAME = "feature_name"
VERSION = "1.0.0"

def register_commands(dispatch: dict) -> None:
    """Add entries to the dispatcher dictionary."""
    ...

def header_sections() -> list[tuple[int, str]] | list[str]:
    """Return (priority, rendered_text) or plain strings."""
    ...

def migrations() -> list[callable]:
    """Return ordered list of migration functions for this feature."""
    ...

def stats_sections() -> dict | None:
    """Optional. Return key→value pairs for the `stats` command."""
    ...

def register_aliases(dispatch: dict) -> None:
    """Optional. Add short aliases (e.g., 'pray' → 'p')."""
    ...
```

### 4.2 Feature registration

Explicit registry in `dailydriver/features/__init__.py`:

```python
from . import prayer, sleep, weather, hygiene, birthday, intention, calendar, journal

ENABLED = [prayer, sleep, weather, hygiene, birthday, intention, calendar, journal]
```

No auto‑discovery – the ordering of `ENABLED` explicitly controls header slot order.

### 4.3 Hard design problems to solve now

- **Header slot ordering** – each feature gets a `header_priority` (or we rely on the registry
  order). This must be consistent before we add more features.
- **Per‑feature migration versioning** – each feature keeps its own migration sequence,
  tracked in `meta` as `migration_version_<feature>`. Implement this as part of the refactor.
- **Database table namespacing** – prefix tables with the feature name where collisions could
  occur (e.g., `weather_cache`, `prayer_logs`).
- **Category system remains global** – keyword learning is a shared service; features don't
  own it but consume it.

### 4.4 Refactor order

1. Pilot with `weather` (most self‑contained).
2. `hygiene`
3. `sleep` + `nap`
4. `prayer`
5. `calendar` + `birthdays`
6. `journal` + `search`
7. Remaining commands (`stats`, `hijri`, `intentions`, `great events`, etc.)
8. Add one new feature (e.g., `نذر` or `people`) through the new system to validate hooks.

Work will happen on the `feature-refactor` branch; `main` stays stable until merge.
