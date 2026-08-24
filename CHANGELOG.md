# Changelog

## Unreleased

### Added
- **Category editor** (`tools/category_editor.py` + `category_editor.html`,
  port 8768) for long-term category maintenance: list categories by usage
  (with live search and per-category entry previews), rename (case-insensitive
  uniqueness, path-shape validation), merge (transactional: entry references
  re-pointed, per-entry duplicate references removed, keyword counts summed,
  source category and keywords removed), and safe delete (empty categories
  only). Smart merge suggestions via normalised Levenshtein similarity
  (≥ 0.80) with one-click pre-filled merge. Renames keep the active great
  event's stored category paths consistent and warn when a hygiene item's
  path-suffix match would be broken. Destructive actions require typed
  confirmation; all mutations run in a single transaction that rolls back on
  failure.

## 2.0.0 (2026‑08‑24)

### BREAKING
- **`bd` is now fully interactive** – birthday creation no longer accepts inline
  `name date` arguments (e.g. `bd Ali 1386/05/12`). Run `bd` and answer the
  prompts. Logging commands keep their inline syntax; only creation moved fully
  interactive.

### Added
- **prompt_toolkit input backend** – the REPL prompt gains command
  autocompletion and persistent history, and the journal category picker becomes
  an autocompleting, ranked selector. The category dropdown is ordered by
  relevance (20 ranked entries, then the rest of the catalog alphabetically),
  drops entries you've already committed on the line (by name or by number), and
  reserves enough height to show plenty at once without scrolling the header off.
  Pressing Enter on an empty line always accepts suggestion #1 (`0` is the
  explicit opt-in for "Great Event only"). Output stays plain text. When
  prompt_toolkit is unavailable or stdin/stdout is not a TTY (piped input,
  redirects, most test contexts), the app silently falls back to plain prompts
  and behaves exactly as before. Adds a `prompt_toolkit>=3` dependency.
- **`-h` / `--help` on every command** – built from a single help registry
  (`cli/help_registry.py`). The `?` / `h` summary is generated from the same
  source, so per-command help and the overview can no longer drift apart. Help
  flags are matched as exact tokens, so leading-dash arguments like `p -15` are
  never mistaken for help.
- **Documentation** – a full `docs/` tree: getting started, per-feature command
  pages, concept guides (time expressions, categories, header, calendars, day
  start), an architecture guide, and a roadmap built from real release history.

### Changed
- **Unified export timeline** – `export` renders one chronological timeline
  interleaving journal entries with sleep, naps, prayers, qada progress, and
  target logs, grouped by day. Features contribute items through a new
  `export_items(conn, cutoff)` hook in the feature contract (documented in
  `features/HOOKS.md`); the void scratchpad stays separate (`vexport`).
  Markdown remains the default (`--md`/`--txt`).
- **Category suggestion ranking** – exact matches are now detected on whole path
  segments (split on `/` and non-alphabetic characters, stemmed), eliminating
  substring false positives like `art`→`start` or `log`→`blog`. The exact-match
  boost is a gentle, coverage-proportional tiebreaker (scaled to the strongest
  TF-IDF score, with a floor), and a fully covered path earns an extra bonus so a
  full exact match outranks a deeper partial one (e.g. `free_learning` beats
  `free_learning/art` for "learning"). IDF is clamped at 0. The numbered picker
  now shows 5 suggestions; the rich dropdown ranks 20.
- **Command dispatch unified** – the REPL and single-command paths share one
  `_dispatch_line` helper (help interception + handler/journal routing).
- **Header event lines** – the great-event and running-event status lines are
  built into the priority-ordered header stream at their historic position (just
  under prayers, above sleep). A refactor had stopped rendering them entirely;
  they are restored without reintroducing a feature package.
- **Documentation restructure** – `COMMANDS.md`, `OPTIMIZATIONS.md`, `TODO.md`,
  and `REVIEW_ACTIONS.md` removed from the repository root; their content is
  rewritten into `docs/` (command pages, `docs/reference/optimizations.md`, and
  `docs/roadmap.md`). Root keeps a slimmed `README.md`, `CONTRIBUTING.md`,
  `CHANGELOG.md`, and `LICENSE`.

### Fixed
- **Target progress now updates `last_action`** – progress logs are real logged
  activity (and part of the unified export timeline), so they now refresh the
  chaining timestamp on commit like other writes.
- **Great/running event never shown in the header** – a pre-existing regression
  from the v1.8.0 feature-package refactor (the header builder stopped calling
  the event status helpers). Restored, so `sge`/`se` are visible and clearly
  disappear on `ege`/`ee`/`cge`/`ce`.
- **`ege`/`ee` silently kept the event when logging was cancelled** – if the time
  confirmation was declined, the entry wasn't logged *and* the event wasn't
  cleared, with no feedback. The event is intentionally kept (so nothing is lost)
  but now says so explicitly and tells you how to end or cancel it. Long-standing
  bug, not new to v2.0.

### Tests
- Added coverage for category ranking (including full-vs-partial preference), the
  prompt_toolkit backend and fallback (live dropdown removal, dedupe, empty-Enter
  semantics), the help system (flag detection, alias resolution, summary
  generation, and a guard that every registered command has a help entry), the
  fully interactive `bd`, header event placement/ordering, and the cancelled-log
  event paths. Suite at **456 passing tests**.

## 1.8.0 (2026‑08‑23)

### Added
- **Multiple sleep sessions per day** – removed single-entry restriction on `sleep_logs` (migration v1). Daily header now shows total duration and individual time ranges.
- **Sleep analysis tool** – `tools/sleep_avg.py` computes true daily sleep and nap averages across any date range (unlogged days counted as 0).
- **New Jalali event** – Martyrdom of Mohsen Hojaji (2017).

### Changed
- **Feature package architecture overhaul** – formalized capability-based feature contracts (`NAME`, `VERSION`, `register_commands`, `header_sections`, `migrations`). Removed monolithic `_logic.py`/`_header.py`/`_manager.py` files across all features in favor of domain modules (`commands`, `manager`, `editor`, `schedule`, `table`, etc.). Aliases now registered directly in `register_commands`.
- **Presentation & registry helpers** – added `features/presentation.py` for shared terminal UI formatting and `features/registry.py` for feature validation. Documented contract in `features/HOOKS.md`.
- **Nap header** – now displays interval time ranges consistent with sleep.

### Fixed
- **Qada nudges** – overdue entries now persistently shown in header nudges; today's scheduled instances shown only in the final hour before prayer. Nudges sorted chronologically.
- **Hijri offset** – fixed offset for Rabi al-Awwal in `data/hijri_offset.txt`.
- **Code style** – applied `isort` and `black` formatting across the codebase.

### Tests
- **Test suite rewrite** – rebuilt entire test suite around package boundaries (`tests/cli/`, `tests/core/`, `tests/display/`, `tests/features/`, `tests/integration/`, `tests/ui/`, `tests/utils/`). Isolated SQLite template fixture, deterministic `ui` recorder, and expanded to **395 passing tests**.

## 1.7.0 (2026‑08‑04)

### BREAKING
- **qada command overhaul** – previously an alias for `p q`, now a full feature with its own manager and sub‑commands (`qada`, `qada log`, `qada fasting`). The old `p q` behaviour remains unchanged; `qada` now opens an interactive backlog manager.

### Added
- **qada feature** – interactive manager for prayer backlog and fasting tracking. Fixed 4 entries (Fajr, Dhuhr/Asr, Maghrib/Isha, Fasting) with progress tracking, pause/unpause, and interval scheduling.
- **targets feature** – track nazr (finite) and habit (indefinite) goals with `nazr`, `habit`, and `targets` commands. Supports `log`, `daily_total`, `counter_total`, and `counter_reset` sub‑commands.
- **travel mode** – disable location‑dependent features (weather, prayer nudges) with `travel`, `travel on/off/status`. Prayer in travel mode shows a smart slot selector.
- **day_start_hour** – shift the day boundary (default 4:00 AM) for hygiene and targets with `daystart` and `daystart <0-23>`.
- **void feature** – scratchpad for unfiltered thoughts (`v`, `void`, `vexport`). Separate from the main journal, does not update `last_action`.
- **u / update command** – manually refresh `last_action` timestamp for chaining.
- **termux-dialog integration** – `-md` / `--termux-dialog` flag opens an Android text dialog for quick journal entries.
- **hygiene manager overhaul** – dynamic table with sorting by urgency, color‑coded rows (red = overdue, yellow = today), smart interval display, and cleaner edit/delete flows.

### Changed
- **`p q`** – now logs at the current time instead of the fixed prayer time (more natural for qada).
- **`hijri`** – now always interactive (no arguments accepted).
- **`export`** – Markdown is the default format (use `--txt` for plain text).
- **`recent`** – layout now matches `view` and `search` (was renamed from `last` earlier).
- **Hijri offset** – now correctly applied in the header display (previously subtracted instead of added).

### Fixed
- **Hygiene** – respect `day_start_hour` for nudges and manager (entries before 4 AM now count towards the previous day).
- **Qada scheduler** – fixed `compute_pending_instance` to use the last log's `instance_date` correctly.
- **Qada migration** – preserved existing logs when dropping `qada_declines` and `paused_from`.

### Tests
- Test suite now at **293 passing tests**.

## 1.6.0 (2026‑06‑19)

### Changed
- **Feature‑package architecture** – extracted 8 domains into `dailydriver/features/` (weather, hygiene, birthdays, sleep/nap, intentions, calendar, events, prayer). Each feature registers its own commands, header sections, aliases, and migrations via a standard hook interface. Core infrastructure (`database`, `migration`, `keyword_learner`, `display_utils`) remains shared.
- **Dispatcher unified** – all command handlers now accept a raw line string; loader loops call `register_commands` and `register_aliases` hooks on each feature.
- **Test suite overhaul** – added a comprehensive dispatch smoke test (verifies every handler’s arity) and a full‑stack smoke test (exercises every command). Test runner unified on `pytest`. 163 tests passing.

### Fixed
- Broken `se`/`ce`/`year` commands after dispatcher refactor (now wrapped in lambda wrappers).
- Missing `sleep` alias after feature extraction (aliases loader wired).
- Stale imports and dead code across the codebase (ruff cleanup).

## 1.5.0 (2026‑05‑29)

### Added
- **Reminder overhaul** – calendar events have permanent numeric IDs; reminder levels (0/1/2) stored in new `event_reminders` table and `birthdays.remind_level` column. Configurable lead‑time schedules (multiples of 7). Per‑event holiday alignment. Reminder editor (`tools/reminder_editor.py` + HTML) for visual level selection. Tomorrow preview in header.
- **Birthday manager** – interactive `birthdays` command to list, toggle reminder levels, add, and delete birthdays. `bd` command extended to accept an optional `remind_level` argument.
- **New Hijri event** – Martyrdom of Muslim ibn Aqil (AS).
- **Weather translation** – added thunderstorm condition.
- **Test isolation** – database path configurable via `DAILYDRIVER_DB` env var; `conftest.py` and updated `run_all.py` run all tests against a temporary database. Clean‑clone test runs are green. 161 tests total.

### Changed
- **Dispatcher unified** – all command handlers now accept the raw `line` string. Removed duplicated `first in (…)` tuple from `repl()` and `run_single_command()`.
- **Post‑handler logic extracted** – `_show_result()` helper deduplicates header‑redisplay code.
- **Birthday display** – unified into a single schedule‑based function; all birthdays appear as their own line in the header.
- **Calendar event display** – duplicate suppression for events already shown as today/tomorrow reminders; holiday alignment only when a visible holiday is present.
- **Birthday manager layout** – dynamic column widths with word‑wrapped names.
- **Weekday abbreviation restored** in the header date line.
- **Eid al‑Adha title** updated to "Eid‑e Qorban / Eid al‑Adha".
- **Modern cultural figures removed** from Jalali calendar events.
- **Bumped `requires‑python`** to `>=3.10`.

### Fixed
- `exit()` replaced with `sys.exit(0)` in the quit handler.
- Clean‑clone test failures eliminated (database path resolution).

## 1.4.0 (2026‑05‑21)

### Added
- **Unified time‑expression language** – a single, powerful parser (`parse_time_expressions`) for all time input. Supports single times (`09:18`), ranges (`09:18‑09:24`, `‑15‑n`), `l`/`last` and `n`/`now` atoms, durations (`5m`, `1h30m`), and offsets (`‑15`, `‑‑15m`, `l+5m`). AM/PM disambiguation with 24h auto‑detection. Used by journal, sleep, nap, and prayer.
- **Header redesign** – modern, centered date block with Jalali weekday, thin proportional separator, and Gregorian/Hijri dates. Prayer placeholders fixed to 5‑char width. Sleep and nap combined into one spread line. Birthdays formatted `🎈 Name 2d · 48`. Bottom bar minimal, right‑aligned. Breather lines between sections.
- **`recent` command** – renamed from `last`; layout now matches `view` and `search` with wrapped categories and descriptions.
- **120+ new tests** – covering the unified time parser, sleep/nap parser, logger time‑conversion, date parser, hijri offset, hygiene nudges, prayer backlog, terminal UI confirmations, and multiline routing. Total: **148 tests**.
- **Linting & formatting** – Ruff auto‑fix + manual cleanup (zero warnings). Black and isort applied with 120‑char line length for uniform code style.

### Changed
- **Event‑command display order** – `se`, `ce`, `ee`, `ln` now follow the same pattern as `sge`/`ege`/`cge`: operation → clear → updated header → confirmation message.
- **Sleep / nap** now use the unified parser and accept `l`/`n`/`ln` ranges (e.g., `s l‑9`, `s 23‑n`, `s ln`, `nap l‑‑5`). Nap interactive prompts removed.
- **`p` offset** uses the unified parser (e.g., `p ‑15` logs prayer time minus 15 minutes).
- **`ege` in multiline mode** (`:m`) is now properly routed to `end_great_event_cmd`.
- **Time confirmation** no longer repeats when a time is explicitly picked from a suggestion list.
- **`date_str` removed** from the header data dict; the old top‑border code deleted.

### Fixed
- `_save_entry` now correctly receives Unix timestamps from the new parser (no more `TypeError` on `l6m` etc.).
- SQLite FTS index kept in sync with new and edited entries (migration v8 for final rebuild, migration v9 for meta table consolidation).
- Various import, variable, and dead‑code cleanup across the entire codebase.

## 1.3.0 (2026‑05‑13)

### Added
- **State files moved into database** – `.daily_last_action`, `.daily_pending`, and `.daily_great_event` are now stored in the `meta` table. Migration v10 imports existing state and deletes the old dot‑files.
- **Commander split into command modules** – `cli/commands/` directory with one file per feature group, plus a clean `dispatcher.py` mapping commands to handlers. Greatly simplifies maintenance and testing.
- **Built‑in aliases** – `pray` → `p`, `sleep` → `s`, `h` → `?`, `qada` → `p q`.
- **Global Hijri date offset** – stored in `data/hijri_offset.txt` (version‑controlled). New interactive `hijri` command shows today’s Hijri date with offsets and applies the chosen correction to all Hijri calendar events. Events cache is invalidated immediately on change.
- **Terminal UI polish** – color‑coded prayer nudges (red overdue, yellow pre‑alert), reverse‑video calendar today highlight (`cal` and `year`), dimmed past‑day header, bold navigation prompts, search result text highlighting, soft‑wrapped calendar event lines.
- **Nap command simplified** – now only accepts start/end times (like `s`), no interactive prompts.
- **Calendar event additions** – Dahw al‑Ard added to Hijri events; weather condition translations for dusty / blowing dust.
- **Test coverage** – new test suites for the modularized header (10 files), database‑backed logger state, dispatcher, and event commands. All tests use in‑memory databases.

### Changed
- **Header modularized** – `build_header_data` split into dedicated helper modules (`prayer`, `sleep`, `birthdays`, `hygiene`, `calendar`, `events`, `weather`) under `display/header/`.
- **is_past → is_today refactor** – cleaner logic for past/present/future day views; nudges are constrained to today.
- **Export defaults to Markdown** – `export 7d` now produces a `.md` file with formatted tables, emojis, and day separators. Plain text available via `--txt`.
- **Prayer backlog overhaul** – `rq` / `mp` replaced by `p q` with flexible time arguments (`-15`, `03:11`), smart overdue detection, and auto‑advancing `prayer_complete_until` meta key. Pre‑alert and overdue nudges now appear in the header.
- **ANSI‑aware display width** – `pline`, `spread_line`, and header centering now strip escape codes before measuring, so colors and formatting never misalign.
- Various Pyright type‑safety fixes (optional member access, missing imports, parameter name mismatches).

### Fixed
- Auto‑commit in `get_connection_cm` now ensures all database‑backed state helpers (`se`, `ce`, `sge`, `ege`, `cge`) persist immediately.
- FTS index now kept in sync with new and edited entries (migration v8 for final rebuild).
- Search scoring fixes (FTS rank formula, exact‑word bonus, category boost split).
- Calendar event import corrected to use Gregorian dates for slot‑time comparisons.

## 1.2.0 (2026‑05‑08)

### Added
- **Weather integration** – Tehran weather scraped from IRIMO, cached hourly, with offline fallback.  
  Shows temperature, condition emoji, and timestamp in the daily header.  
  Past‑day views display the cached weather for that date.
- **`day` / `today` command** – view any past day with navigation (`p`/`n`) and direct date input (`YYYY‑MM‑DD`).  
  Header adapts to the target date (prayers, sleep, weather, events).  
  Added `d` shortcut in `view` and `search` to jump to an entry’s day.
- **Per‑calendar icons** – Jalali 🔆, Gregorian 🌐, Hijri 🌙, with holiday confetti 🎊, now used in header, `cal`, and year view.
- **Multi‑page navigation** in `view` and `search` – use `n`/`p` with optional count (e.g. `5n` jumps 5 pages) and prompts now show `n/p = next/prev page, 5n = 5 pages`.

### Changed
- **Search scoring overhaul** – FTS rank formula strengthened (10/abs(rank)), exact‑word matches get +2.0 bonus, category boosts split (exact word +5.0, substring +1.0), LIKE fallback uses OR.
- **Keyword system** – stemmed existing keywords via Porter2 stemmer (migration v5), removed pending‑keywords table, added `count` column for TF‑IDF.
- **Sleep display** – duration now shown before the time range in the header.
- **Header bottom bar** – now shown for past days too.
- English weekday abbreviation prepended to the date in the header (e.g., `Sat, 18 Ordibehesht 1405`).

### Fixed
- `cge` command now accepts optional argument (dispatch compatibility).
- Editor save now persists deletes immediately.
- `ege` no longer clears great event when logging is cancelled.
- Export now shows naps and correctly formatted prayer times.
- Various import and pagination glitches in search/view.

## 1.1.0 (2026‑05‑05)

### Added
- **Full‑text search** (`search` command) using SQLite FTS5 with LIKE fallback and fuzzy scoring.
- **Fuzzy search boosts** for time‑of‑day (morning/afternoon/night), relative dates (yesterday, last week, weekdays, months), and categories.
- **Nap logging** (`nap` command) to track short sleep periods – start time, duration, and optional description.
- **Keyword editor** (`tools/keyword_editor.py` + `keyword_editor.html`) for pruning keywords and adding stopwords.
- **Event editor save fix** – deletes now persist immediately.
- **Stemming** (`porter2stemmer`) for keyword learning and search queries – handles plurals, possessives, and contractions.
- **Morphological tokenizer** – properly splits hyphenated words, removes possessives, and stems tokens.

### Changed
- **Keyword system overhaul** – replaced raw frequency with TF‑IDF + exact‑path boost (up to 10 suggestions).
- **Search** uses `OR` logic for forgiving multi‑word queries.
- **Calendar event display** switched to English titles (`title_en`), with Persian preserved as `title_fa`.
- **`nap` export** shows start‑end times (like sleep).
- **Naps** now appear in daily header and `today` summary.

### Fixed
- `ege` no longer clears the great event when logging is cancelled.
- `cge` command now accepts an optional argument (dispatch compatibility).
- Entry viewer shows Jalali dates in `YYYY‑MM‑DD` format.
- `last X mins` time parsing now works correctly.
- Various import and pagination fixes in `search` and `view`.

### Dependencies
- Added `porter2stemmer` to `pyproject.toml`.
```bash
pip install .
```

## 1.0.0 (2026‑05‑02)

### Added
- Full modular restructure into `dailydriver/` package with clear separation of concerns
- Prayer logging with dynamic Tehran times (monthly interpolation from University of Tehran data)
- Sleep logging with auto‑calculated duration
- Hygiene tracking with configurable intervals and header nudges
- Birthday list (Jalali dates, upcoming birthday alerts)
- Intentions (to‑dos with deadlines)
- Free‑text journal entries with smart time parsing and category suggestions
- Keyword learning from entries for automatic category suggestions
- Great‑event commands (`sge`, `ege`, `cge`)
- Running‑event commands (`se`, `ee`, `ce`)
- Chaining command (`ln`)
- Statistics view (`stats`): prayer adherence, sleep averages, hygiene, top categories
- Today’s summary view (`today`)
- Month calendar view (`cal`) – clean Unix‑style grid, Saturday‑first
- Year calendar view (`year`) – responsive multi‑column display
- Export command (`export`) – human‑readable text files for sleep, prayers, entries
- Three‑calendar event system (Jalali, Gregorian, Hijri) with dynamic date conversion
- Reminder feature (`remind` field) – upcoming events shown in header
- Mobile‑friendly event editor (`tools/edit_events.py` + `editor.html`)
- `pyproject.toml` for packaging and dependency management (install with `pip install .`)
- Comprehensive documentation: `README.md`, `COMMANDS.md`, `CONTRIBUTING.md`
- MIT license

### Changed
- Prayer times are now interpolated monthly instead of using fixed constants
- All state files and database moved to `data/` directory
- Event data stored in three separate JSON files (`events_jalali.json`, `events_gregorian.json`, `events_hijri.json`)
- Command reference split from `README.md` into `COMMANDS.md`

### Fixed
- `ege` now preserves the great event when logging is cancelled
- Various import and path fixes after modularisation
- Calendar event display improved (one event per line in header)

### Dependencies
```bash
pip install jdatetime hijridate
```
