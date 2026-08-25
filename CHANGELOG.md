# Changelog

## Unreleased

### Changed
- **Documentation site migrated to Astro Starlight** – `docs/` is now a
  self-contained Astro site (default Starlight theme, page search, dark mode,
  prev/next links, and an auto sidebar) that builds to `docs/dist` and is
  published to GitHub Pages at `https://msadrashakouri.ir/DailyDriver/` by
  `.github/workflows/docs.yml`. The plain-Markdown pages moved to
  `docs/src/content/docs/` and gained Starlight frontmatter (the old first
  `# heading` becomes the `title`); content, headings, and relative links are
  otherwise unchanged. The GitHub Wiki sync plan (`docs/WIKI-SYNC.md`) was
  dropped in favour of publishing the docs site; root `README`/`CONTRIBUTING`
  links now point to the new source layout and the live site.

### Tests
- Verified passing counts from `v1.6.0` onward: 163 → 293 → 395 → 456 → 500 (`pytest -q` / `tests/run_all.py`).

---

## 2.1.0 (2026-08-24)

### Added
- **Unified day timeline** (`day` view): everything logged that day in
  chronological order — journal entries, prayers 🕌, sleep 💤, naps 😴, qada 📿,
  targets 🎯 — via the same `export_items` builder. Items placed by start time.
- **Day-boundary modes** (`m` toggle): midnight (00:00 → 24:00, default) vs.
  configurable `day_start` hour; mode persisted in meta table.
- **Weekday in export headers**: `Mon, 02 Shahrivar 1405` (Markdown) and
  `── Mon, 02 Shahrivar 1405 ──` (text), derived from Gregorian equivalent.
- **Time ranges in `view` / `search`**: `HH:MM → HH:MM (dur)` format; newest-first
  by start time; `d <id>` jumps to the entry’s start-time day.
- **Category editor** (`tools/category_editor.py` + `category_editor.html`,
  port 8768): alphabetical list (with counts, live search), two-select merge,
  per-category previews, rename (case-insensitive uniqueness + path-shape
  validation), safe delete (empty only), Suggestions tab (top 10 similar pairs,
  normalised Levenshtein, no score floor), typeahead merge dialog. All mutations
  transactional (rollback on failure); typed confirmation required for destructive
  actions.
- First test suites for search, day view, and entry browser.

### Changed
- **Search rewritten as token filter** (no relevance scoring): query words
  tokenized/stemmed; whole-word matches only (`"art"` no longer hits `"start"`);
  results grouped by match count (`all terms` first), newest within group,
  bold cyan headers, `cont.` markers. Matches highlighted in descriptions and
  categories. FTS/fuzzy scoring modules removed; `search yesterday` date boosts
  removed.
- **`export_items` hook**: `export_items(conn, start, end=None)` with optional
  inclusive upper bound; shared by `export` and day timeline. Range-based
  `export YYYY-MM-DD YYYY-MM-DD` CLI remains a roadmap to-do.
- Empty categories now `(no category)` everywhere (export previously `(none)`).
- **Day-view item layout**: three lines — time (range), label/categories (indented),
  description (pulled left) — instead of single prefixed line.
- **Search group headers**: bold cyan, blank-line separated for unmistakable
  transition between match-count groups.

### Fixed
- `pline_wrap` no longer slices ANSI escape codes, which could leak
  reverse-video highlighting into subsequent lines on narrow terminals.

### Tests
- **500 passing** (`pytest -q`) at `v2.1.0`. Previous changelog claim of 456
  likely reflects an intermediate build; 500 is the verified count on the
  tag with full dependency install (`jdatetime`, `hijridate`, `porter2stemmer`,
  `prompt_toolkit>=3`).


---

## 2.0.0 (2026‑08‑24)

### BREAKING
- **`bd` fully interactive** – creation no longer accepts inline `name date`
  (e.g. `bd Ali 1386/05/12`). Logging commands keep inline syntax; only
  creation moved interactive.

### Added
- **`prompt_toolkit` backend** (`>=3`): REPL autocompletion + persistent history;
  category picker is ranked (20 ranked + rest alphabetically), deduped by name/
  number, reserves height, empty-Enter accepts `#1` (`0` opt-in for "Great Event
  only"). Silent fallback to plain prompts when not a TTY or unavailable.
- **`-h` / `--help`** on every command (single registry `cli/help_registry.py`).
  `?` / `h` summary generated from same source; flags matched as exact tokens
  so `p -15` is never mistaken for help.
- **Documentation tree** (`docs/`): getting started, per-feature command pages,
  concept guides (time expressions, categories, header, calendars, day start),
  architecture guide, roadmap from real release history.

### Changed
- **Unified export timeline**: chronological timeline interleaving journal,
  sleep, naps, prayers, qada, targets, grouped by day. Feature contract hook
  `export_items(conn, cutoff)` documented in `features/HOOKS.md`. Void
  scratchpad stays separate (`vexport`). Markdown default (`--md`/`--txt`).
- **Category ranking**: exact matches on whole path segments (`/` + non-alpha
  split, stemmed) eliminates substring false positives (`art` → `start`).
  Gentle coverage-proportional exact-match boost + full-coverage extra bonus.
  IDF clamped at 0. Numbered picker shows 5 suggestions; rich dropdown ranks 20.
- **Command dispatch unified**: REPL and single-command share `_dispatch_line`.
- **Header event lines restored**: great/running event status rebuilt into
  priority-ordered stream under prayers, above sleep (regression from v1.8.0
  package refactor fixed without reintroducing a feature package).
- **Documentation restructure**: `COMMANDS.md`, `OPTIMIZATIONS.md`, `TODO.md`,
  `REVIEW_ACTIONS.md` removed; rewritten into `docs/` (command pages,
  `docs/reference/optimizations.md`, `docs/roadmap.md`). Root keeps slimmed
  `README.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, `LICENSE`.

### Fixed
- **Target progress updates `last_action`** (part of unified export timeline).
- **Great/running event never shown** (header builder regression from v1.8.0).
- **`ege`/`ee` silently kept event when logging cancelled** – event kept
  intentionally (nothing lost) but now confirms explicitly and tells user how
  to end/cancel.



### Tests
- **456 passing** (`v2.0.0`, verified).

---

## 1.8.0 (2026‑08‑23)

### Added
- **Multiple sleep sessions per day**: restriction removed on `sleep_logs`
  (migration v1). Header shows total duration + individual ranges.
- **Sleep analysis tool** (`tools/sleep_avg.py`): true daily sleep/nap averages
  across any date range (unlogged days = 0).
- **New Jalali event**: Martyrdom of Mohsen Hojaji (2017).

### Changed
- **Feature package architecture overhaul**: contracts (`NAME`, `VERSION`,
  `register_commands`, `header_sections`, `migrations`). Monolithic
  `_logic.py`/`_header.py`/`_manager.py` removed; domain modules
  (`commands`, `manager`, `editor`, `schedule`, `table`, etc.). Aliases
  registered directly.
- **Presentation & registry helpers** (`features/presentation.py`,
  `features/registry.py`). Contract documented in `features/HOOKS.md`.
- **Nap header**: interval time ranges consistent with sleep.

### Fixed
- **Qada nudges**: overdue persistently shown; today’s scheduled instances only
  in final hour before prayer. Sorted chronologically.
- **Hijri offset**: corrected `data/hijri_offset.txt` for Rabi al-Awwal.
- **Code style**: `isort` + `black` applied across codebase.

### Tests
- **395 passing** (`v1.8.0`, verified with `tests/run_all.py`).


---

## 1.7.0 (2026‑08‑04)

### BREAKING
- **`qada` command overhaul**: previously alias for `p q`; now full feature
  (`qada`, `qada log`, `qada fasting`) with manager and sub-commands. Old
  `p q` unchanged.

### Added
- **qada feature**: interactive backlog manager; 4 fixed entries (Fajr,
  Dhuhr/Asr, Maghrib/Isha, Fasting); progress tracking, pause/unpause,
  interval scheduling.
- **targets feature** (`nazr`, `habit`, `targets`): finite + indefinite goals;
  `log`, `daily_total`, `counter_total`, `counter_reset`.
- **travel mode** (`travel` / `travel on/off/status`): disables weather and
  prayer nudges; smart prayer slot selector.
- **`day_start_hour`** (`daystart` / `daystart <0-23>`): shifts boundary (default 4:00 AM).
- **void feature** (`v`, `void`, `vexport`): scratchpad; separate from main
  journal; does not update `last_action`.
- **`u` / `update`**: manually refresh `last_action` timestamp.
- **`-md` / `--termux-dialog`**: Android text dialog for quick journal entries.
- **hygiene manager overhaul**: dynamic table with urgency sorting,
  color-coded rows (red overdue, yellow today), smart intervals.

### Changed
- **`p q`**: logs at current time (not fixed prayer time).
- **`hijri`**: always interactive (no arguments).
- **`export`**: Markdown default (`--txt` for plain text).
- **`recent`**: layout matches `view` / `search` (renamed from `last`).
- **Hijri offset**: correctly applied in header (previously subtracted instead
  of added).

### Fixed
- **Hygiene**: respects `day_start_hour` (before 4 AM counts to previous day).
- **Qada scheduler**: `compute_pending_instance` uses last log’s
  `instance_date` correctly.
- **Qada migration**: preserved existing logs when dropping `qada_declines`
  and `paused_from`.

### Tests
- **293 passing** (`v1.7.0`, verified with `tests/run_all.py`).
---

## 1.6.0 (2026‑06‑19)

### Changed
- **Feature-package architecture**: 8 domains extracted to
  `dailydriver/features/` (weather, hygiene, birthdays, sleep/nap, intentions,
  calendar, events, prayer). Standard hook interface for commands, header
  sections, aliases, migrations.
- **Dispatcher unified**: all handlers accept raw `line`; loader loops call
  `register_commands` / `register_aliases`.
- **Test suite overhaul**: smoke tests (dispatch arity + full-stack command
  exercise). Runner unified on `pytest`. 163 passing (verified with `tests/run_all.py`).

### Fixed
- Broken `se`/`ce`/`year` after dispatcher refactor (lambda wrappers).
- Missing `sleep` alias (aliases loader wired).
- Stale imports / dead code (ruff cleanup).

---

 (2026‑05‑29)

### Added
- **Reminder overhaul**: `event_reminders` table; `birthdays.remind_level` column.
  Configurable lead-time schedules (multiples of 7). Per-event holiday alignment.
  Reminder editor (`tools/reminder_editor.py` + HTML). Tomorrow preview in header.
- **Birthday manager**: interactive `birthdays`; toggle reminder levels; add/delete.
  `bd` accepts optional `remind_level` argument.
- **New Hijri event**: Martyrdom of Muslim ibn Aqil (AS).
- **Weather translation**: thunderstorm condition.
- **Test isolation**: `DAILYDRIVER_DB` env var; `conftest.py`; `run_all.py` uses
  temporary DB. Clean-clone runs green. 161 total (historical).

### Changed
- **Dispatcher unified**: all command handlers accept raw `line`.
- **Post-handler logic**: `_show_result()` deduplicates header redisplay.
- **Birthday display**: unified schedule-based function; each birthday its own
  header line.
- **Calendar event display**: duplicate suppression for today/tomorrow reminders;
  holiday alignment only when visible holiday present.
- **Birthday manager layout**: dynamic column widths, word-wrapped names.
- **Weekday abbreviation restored** in header date line.
- **Eid al-Adha title** updated to `"Eid‑e Qorban / Eid al-Adha"`.
- **Modern cultural figures removed** from Jalali events.
- **Bumped `requires-python`** to `>=3.10`.

### Fixed
- `exit()` → `sys.exit(0)` in quit handler.
- Clean-clone test failures eliminated.

---

## 1.4.0 (2026‑05‑21)

### Added
- **Unified time-expression parser** (`parse_time_expressions`): single parser
  for all time input. Supports times (`09:18`), ranges (`09:18‑09:24`, `‑15‑n`),
  `l`/`last` + `n`/`now`, durations (`5m`, `1h30m`), offsets (`‑15`, `‑‑15m`,
  `l+5m`). AM/PM disambiguation with 24h auto-detection. Used by journal,
  sleep, nap, prayer.
- **Header redesign**: modern centered date block (Jalali weekday, separator,
  Gregorian/Hijri), 5-char prayer placeholders, combined sleep/nap spread line,
  birthdays `🎈 Name 2d · 48`, minimal right-aligned bottom bar, breather lines.
- **`recent`**: renamed from `last`; layout matches `view` / `search`.
- **120+ new tests**: time parser, sleep/nap parser, logger conversion, date
  parser, hijri offset, hygiene nudges, prayer backlog, terminal confirmations,
  multiline routing. Total: **148 tests** (historical).
- **Linting & formatting**: ruff + black + isort (120-char line length).

### Changed
- **Event-command display order** (`se`, `ce`, `ee`, `ln`) matches
  `sge`/`ege`/`cge`: operation → clear → updated header → confirmation.
- **Sleep / nap**: unified parser; `l`/`n`/`ln` ranges (`s l‑9`, `nap l‑‑5`).
  Interactive prompts removed.
- **`p` offset**: unified parser (`p ‑15` = prayer time − 15 min).
- **`ege` in multiline mode** (`:m`): properly routed to `end_great_event_cmd`.
- **Time confirmation**: no longer repeats when time explicitly picked.
- **`date_str` removed** from header data dict; old top-border code deleted.

### Fixed
- `_save_entry` receives Unix timestamps correctly (no `TypeError` on `l6m`).
- SQLite FTS index kept in sync (migration v8 final rebuild, v9 meta consolidation).
- Import / variable / dead-code cleanup.

---

## 1.3.0 (2026‑05‑13)

### Added
- **State files moved to DB**: `.daily_last_action`, `.daily_pending`,
  `.daily_great_event` → `meta` table. Migration v10 imports state + deletes
  dot-files.
- **Commander split**: `cli/commands/` (one file per feature group) + clean
  `dispatcher.py`.
- **Built-in aliases**: `pray` → `p`, `sleep` → `s`, `h` → `?`, `qada` → `p q`.
- **Global Hijri offset** (`data/hijri_offset.txt`, version-controlled):
  interactive `hijri` shows offset; correction applied to all Hijri events;
  cache invalidated immediately.
- **Terminal UI polish**: color-coded nudges (red overdue, yellow pre-alert),
  reverse-video calendar today highlight (`cal`/`year`), dimmed past-day header,
  bold navigation prompts, search result highlighting, soft-wrapped event lines.
- **Nap command simplified**: only start/end times (like `s`).
- **Calendar events**: Dahw al-Ard (Hijri); dusty / blowing dust translations.
- **Test coverage**: modularized header (10 files), DB-backed logger state,
  dispatcher, event commands. In-memory DB for all.

### Changed
- **Header modularized**: `build_header_data` split (`display/header/`).
- **`is_past → is_today` refactor**: cleaner past/present/future logic; nudges
  constrained to today.
- **Export defaults to Markdown**: `.md` with formatted tables, emojis,
  day separators. Plain text (`--txt`).
- **Prayer backlog overhaul** (`rq`/`mp` → `p q`): flexible times (`-15`, `03:11`),
  smart overdue detection, auto-advancing `prayer_complete_until`. Pre-alert
  and overdue nudges in header.
- **ANSI-aware display width**: `pline`, `spread_line`, header centering
  strip escape codes before measuring.
- **Pyright fixes**: optional member access, missing imports, parameter names.

### Fixed
- Auto-commit in `get_connection_cm` ensures DB-backed state helpers persist.
- FTS index sync (v8 final rebuild).
- Search scoring (FTS rank, exact-word bonus, category boost split).
- Calendar event import uses Gregorian dates for slot-time comparisons.

---

## 1.2.0 (2026‑05‑08)

### Added
- **Weather integration**: Tehran weather scraped from IRIMO, hourly cache,
  offline fallback. Temperature, condition emoji, timestamp in daily header.
  Past-day views show cached weather for that date.
- **`day` / `today` command**: view any past day (`p`/`n` navigation,
  direct `YYYY-MM-DD` input). Header adapts to target date. `d <id>` shortcut
  in `view` / `search`.
- **Per-calendar icons**: Jalali 🔆, Gregorian 🌐, Hijri 🌙; holiday confetti 🎊.
- **Multi-page navigation** (`view` / `search`): `n`/`p` + optional count
  (e.g. `5n`); prompts show `n/p = next/prev page, 5n = 5 pages`.

### Changed
- **Search scoring overhaul**: FTS formula (`10/abs(rank)`), exact-word
  bonus `+2.0`, category boost split (exact `+5.0`, substring `+1.0`), LIKE
  fallback uses `OR`.
- **Keyword system**: stemmed via Porter2 (migration v5), removed
  `pending_keywords` table, added `count` column for TF-IDF.
- **Sleep display**: duration shown before time range in header.
- **Header bottom bar**: shown for past days too.
- **English weekday abbreviation** prepended to date (`Sat, 18 Ordibehesht 1405`).

### Fixed
- `cge` accepts optional argument (dispatch compatibility).
- Editor save persists deletes immediately.
- `ege` no longer clears great event when logging cancelled.
- Export shows naps + correctly formatted prayer times.
- Import / pagination glitches in `search` / `view`.

---

## 1.1.0 (2026‑05‑05)

### Added
- **Full-text search** (`search`): SQLite FTS5 + LIKE fallback + fuzzy scoring.
- **Fuzzy boosts**: time-of-day (morning/afternoon/night), relative dates
  (yesterday, last week, weekdays, months), categories.
- **Nap logging** (`nap`): start time, duration, optional description.
- **Keyword editor** (`tools/keyword_editor.py` + `keyword_editor.html`).
- **Event editor save fix**: deletes persist immediately.
- **Stemming**: `porter2stemmer` for keywords and search (plurals, possessives,
  contractions).
- **Morphological tokenizer**: splits hyphenated words, removes possessives,
  stems tokens.

### Changed
- **Keyword system overhaul**: TF-IDF + exact-path boost (up to 10 suggestions).
- **Search `OR` logic** for forgiving multi-word queries.
- **Calendar events**: switched to English titles (`title_en`); Persian preserved
  as `title_fa`.
- **`nap` export**: start-end times (like sleep).
- **Naps**: appear in daily header and `today` summary.

### Fixed
- `ege` no longer clears great event when logging cancelled.
- `cge` accepts optional argument (dispatch compatibility).
- Entry viewer shows Jalali dates in `YYYY-MM-DD` format.
- `last X mins` time parsing works correctly.
- Import / pagination fixes in `search` and `view`.

### Dependencies
- Added `porter2stemmer` to `pyproject.toml`.
```bash
pip install .
```

---

## 1.0.0 (2026‑05‑02)

### Added
- Full modular restructure (`dailydriver/` package): clear separation of concerns.
- Prayer logging: dynamic Tehran times (monthly interpolation from University
  of Tehran data).
- Sleep logging with auto-calculated duration.
- Hygiene tracking: configurable intervals + header nudges.
- Birthday list (Jalali dates, upcoming alerts).
- Intentions (to-dos with deadlines).
- Free-text journal entries: smart time parsing + category suggestions.
- Keyword learning: automatic category suggestions from entries.
- Great-event commands (`sge`, `ege`, `cge`).
- Running-event commands (`se`, `ee`, `ce`).
- Chaining (`ln`).
- Statistics (`stats`): prayer adherence, sleep averages, hygiene, top categories.
- Today’s summary (`today`).
- Month calendar (`cal`): Unix-style grid, Saturday-first.
- Year calendar (`year`): responsive multi-column.
- Export (`export`): human-readable text files (sleep, prayers, entries).
- Three-calendar events (Jalali, Gregorian, Hijri): dynamic date conversion.
- Reminder feature (`remind`): upcoming events in header.
- Mobile event editor (`tools/edit_events.py` + `editor.html`).
- `pyproject.toml`: packaging + dependency management (`pip install .`).
- Documentation: `README.md`, `COMMANDS.md`, `CONTRIBUTING.md`.
- MIT license.

### Changed
- Prayer times: monthly interpolation (not fixed constants).
- State + DB moved to `data/`.
- Events in three JSON files (`events_jalali.json`, `events_gregorian.json`,
  `events_hijri.json`).
- Command reference split: `README.md` → `COMMANDS.md`.

### Fixed
- `ege` preserves great event when logging cancelled.
- Import / path fixes after modularisation.
- Calendar event display: one event per line in header.

### Dependencies
```bash
pip install jdatetime hijridate
```