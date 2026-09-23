# Changelog

## Unreleased

### Added

- **Prayer windows, deadlines, and colors**: each merged slot now opens at its adhan and runs to a fiqh deadline — Fajr to sunrise, Dhuhr & Asr to sunset, Maghrib & Isha to shar'i midnight (the midpoint of sunset to the next Fajr adhan, per Khamenei's risala). The offline solar solver gained sunrise/sunset (0.833°), the fadilat boundaries (اسفار −14°, post-zuwal shadow = gnomon, زوال شفق −14°), and shar'i midnight, all parameterized by (lat, lon, tz) and validated against Iranian published tables for Tehran, Karaj, Qom, and Mashhad. Header nudges became a three-band state machine: yellow pre-alert in the final hour, then one colored `slot — until HH:MM` line (green inside the فضیلت window, yellow for the gap, red for the last 30 min / 2 h), then a red overdue line; logged slots drop their line and past-day overdue nudges are unchanged.

- **Multi-city support**: a version-controlled city registry (`data/cities.json`, shipping Tehran, Karaj, Qom, and Mashhad with coordinates and IRIMO weather URLs), two append-only core migrations for `city_rules` (weekly weekday windows, Saturday-first, overlaps rejected at save) and `city_state` (default city + override), and a pure `resolve_city()` in the new `core/location/` package with precedence travel > override > schedule > default. The new interactive `city` command edits the default, the weekly schedule, and the override (next schedule change / specific datetime / indefinite). Prayer times follow the resolved city's coordinates; weather is fetched and cached per city and displays the city — `☀️ 32°C clear (Karaj) 14:30`, extending to `(Karaj, until 18:00)` when a schedule rule ends within two hours. Cities without an IRIMO page keep prayer times but no weather line.

### Fixed

- **City schedule editor corrupted multi-day input**: `'0 2'` had its spaces stripped and was parsed as the single number 02 — i.e. Monday only — while `'3 4'` (34) was rejected. Day input now treats spaces and commas as separators and also accepts day names (`sat mon`), ascending ranges (`0-4`, `mon-fri`), and Persian digits. Invalid input re-prompts only the failed field instead of discarding the city and days already entered; saved rules echo exactly what was stored; and the upcoming-transitions preview now includes dates (`Sat 26 Sep 07:00 -> Karaj`) so successive weeks are no longer rendered as identical lines.

### Fixed

- **City manager polish (round 2)**: dropped the internal id column — rules are selected by list row number, qada-style (`e 2`, `d 1`); prompts are short labeled fields with hint lines above (`Days (Enter=cancel)` under `e.g. '0 2' 'sat mon' '0-4' 'all'`); blocks gained breathing room; help renders as a box on wide terminals and plain stacked lines on narrow ones; and everything below 64 columns switches to one-command-per-line so a 50-column display never wraps. The upcoming-transitions list stacks one per line with dates at every width.

### Tests

- This branch passes **640 tests** with `pytest -q`, including a seasonal invariant sweep asserting every computed prayer band is positive and correctly ordered (opens < green < yellow-start < red-start < deadline) for all four registry cities across solstices and equinoxes.

---

## 2.2.0 (2026-09-19)

### Added

- **Iranian-first offline Hijri calendar**: bundled month-start data, calculated fallback coverage, month-specific manual corrections, and the existing global correction command retained for compatibility.
- **Offline Tehran prayer calculation**: deterministic coordinate-based solar times using Tehran coordinates, the UTC+03:30 civil timezone, Fajr at 17.7°, and Shia Maghrib at 4.5°, with no runtime network request.

### Changed

- **Prayer header nudges** now use minute-resolution countdowns instead of five-minute buckets and show `due now` during the final minute.
- **Built-in English stemming** replaced the `porter2stemmer` dependency with a compact Porter2-compatible implementation used by keyword learning, search, migrations, and the stopword analysis tool.
- **Stopword maintenance** expanded the stopword list and removed historical noise from the tracked data.
- **Documentation site** migrated to Astro Starlight. The site is built from plain Markdown in `docs/`, published to GitHub Pages, and no duplicate generated documentation is committed.
- **Internal cleanup** centralized prayer labels and lookups, typed prayer arguments, shared duration formatting, safe persisted-state parsing, and qada progress imports while preserving existing command output and compatibility shims.

### Tests

- The `v2.2.0` release candidate passes **533 tests** with `pytest -q`.

---

## 2.1.0 (2026-08-24)

### Added

- **Unified day timeline**: the `day` view shows journal entries, prayers, sleep, naps, qada, and targets in chronological order through the shared `export_items` timeline builder. Items are placed by start time, falling back to log time.
- **Day-boundary modes**: `m` toggles between a midnight day and the configured day-start boundary, with the last-used mode persisted in the `meta` table.
- **Weekday export headers**: Markdown and text exports include abbreviated weekdays derived from the Gregorian equivalent of the Jalali date.
- **Time ranges in `view` and `search`**: entries with durations display `HH:MM → HH:MM (dur)`, sort by start time, and support `d <id>` to jump to the entry's day.
- **Category editor**: `tools/category_editor.py` and its HTML UI provide live search, entry previews, rename, transactional merge, safe delete, similar-category suggestions, and a typeahead merge dialog on port 8768.
- **Search, day-view, and entry-browser test suites**.

### Changed

- **Search** was rewritten as a token filter rather than a relevance scorer. Queries and entries use stemming, matching is whole-word based, results are grouped by the number of matching terms, and matches are highlighted in descriptions and category paths. The former FTS/fuzzy scoring modules and date boosts were removed.
- **`export_items`** now accepts `start` and an optional inclusive `end` bound, allowing the same feature hook to serve exports and the unified day timeline.
- Empty categories consistently render as `(no category)` instead of `(none)`.
- Day-view items render as separate time, label/category, and description lines.
- Search group headers are visually separated with bold cyan styling and continuation markers.

### Fixed

- `pline_wrap` no longer slices ANSI escape sequences while truncating highlighted text.

### Tests

- The `v2.1.0` tag passed **500 tests** with `pytest -q`.

---

## 2.0.0 (2026-08-24)

### Breaking changes

- **`bd` is fully interactive**: birthday creation no longer accepts inline `name date` arguments such as `bd Ali 1386/05/12`. Logging commands retain their inline syntax.

### Added

- **`prompt_toolkit` input backend**: the REPL has command completion and persistent history, and the category picker has ranked completion, duplicate removal, reserved display space, and Enter-to-accept behavior. It falls back to plain input when the dependency is unavailable or the process is not attached to a TTY.
- **Unified help**: every command supports `-h` and `--help`, while `?` and `h` use the same registry to build the summary. Help flags are exact tokens, so arguments such as `p -15` are not misinterpreted.
- **Documentation tree**: command pages, concept guides, an architecture guide, and a roadmap moved into `docs/`.

### Changed

- **Unified export timeline**: `export` interleaves journal entries, sleep, naps, prayers, qada progress, and targets by day through the new `export_items` feature hook. The void scratchpad remains separate through `vexport`, and Markdown remains the default output.
- **Category ranking** now matches complete path segments instead of substrings, eliminating false positives such as `art` matching `start`. The exact-match boost is coverage-aware, full path matches receive an extra bonus, IDF is clamped at zero, and the numbered picker shows five suggestions while the rich picker ranks twenty.
- **Command dispatch** now shares one raw-line dispatch path between the REPL and single-command mode.
- **Header event lines** were restored to their historic position beneath prayers and above sleep.
- **Documentation layout** was consolidated into `docs/`; the old root command, optimization, roadmap, and review documents were removed or replaced by the new structure.

### Fixed

- Target progress logs now update `last_action` because they are real logged activity and appear in exports.
- Great-event and running-event status lines are visible again after the feature-package refactor and disappear correctly when their events end.
- Cancelling an `ege` or `ee` time confirmation now explains that the event was intentionally kept and how to end or cancel it.

### Tests

- The `v2.0.0` tag passed **456 tests** with `pytest -q`.

---

## 1.8.0 (2026-08-23)

### Added

- **Multiple sleep sessions per day**: the single-entry restriction was removed, and the header shows total sleep duration plus each individual range.
- **Sleep analysis tool**: `tools/sleep_avg.py` calculates daily sleep and nap averages across a date range, counting unlogged days as zero.
- **Jalali calendar event**: added the Martyrdom of Mohsen Hojaji (2017).

### Changed

- **Feature package architecture** was formalized around capability-based contracts: `NAME`, `VERSION`, `register_commands`, `header_sections`, and `migrations`. Monolithic `_logic.py`, `_header.py`, and `_manager.py` modules were replaced with responsibility-focused domain modules.
- **Feature helpers** were centralized in presentation and registry modules, and the contract was documented in `features/HOOKS.md`.
- Nap header output now uses interval ranges consistent with sleep output.
- The test suite was rebuilt around package boundaries with isolated SQLite fixtures, deterministic UI recording, and feature/integration coverage.

### Fixed

- Qada overdue nudges persist, while today's scheduled qada instances appear only during the final hour before the prayer and are sorted chronologically.
- The Hijri offset data for Rabi al-Awwal was corrected.
- Ruff, isort, and Black cleanup was applied across the codebase.

### Tests

- The `v1.8.0` tag passed **395 tests** with `pytest -q`.

---

## 1.7.0 (2026-08-04)

### Breaking changes

- **`qada` became a full feature** with `qada`, `qada log`, and `qada fasting` commands instead of being only an alias for `p q`. The original `p q` flow remains available.

### Added

- **Qada manager**: tracks Fajr, Dhuhr/Asr, Maghrib/Isha, and fasting progress with pause/unpause and interval scheduling.
- **Targets**: `nazr`, `habit`, and `targets` support finite and indefinite goals, quick logging, daily totals, counter totals, and counter resets.
- **Travel mode**: `travel` and `travel on/off/status` disable weather and prayer nudges and provide a smart prayer-slot selector.
- **Configurable day start**: `daystart` and `daystart <0-23>` shift the boundary used by the application, defaulting to 4:00 AM.
- **Void scratchpad**: `v`, `void`, and `vexport` store private entries separately from the journal without updating `last_action`.
- **`u` / `update`**: manually refreshes the chaining timestamp.
- **Termux dialog input**: `-md` and `--termux-dialog` provide Android text-dialog entry.
- **Hygiene manager overhaul**: dynamic tables, urgency sorting, color-coded rows, and smarter intervals.

### Changed

- `p q` now logs at the current time rather than at a fixed prayer time.
- `hijri` is always interactive.
- `export` defaults to Markdown, with `--txt` for plain text.
- `recent` replaced `last` and now uses the `view`/`search` layout.
- Hijri offsets are added in the header rather than subtracted.

### Fixed

- Hygiene calculations respect the configured day-start hour.
- The qada scheduler uses the last log's `instance_date` correctly.
- Qada migrations preserve existing logs when obsolete decline and pause fields are removed.

### Tests

- The `v1.7.0` tag passed **293 tests** with `pytest -q`.

---

## 1.6.0 (2026-06-19)

### Added

- **Feature package system**: weather, hygiene, birthdays, sleep/nap, intentions, calendar, events, and prayer were extracted into `dailydriver/features/` packages with registry-based discovery and feature-owned migrations.
- **Feature hook contract**: feature packages can register commands, contribute header sections, and expose migrations through a common interface.
- **Weather support** for dust-storm conditions and corresponding ignore rules for generated artifacts.

### Changed

- **Dispatcher unification**: handlers receive the raw command line, and the loader registers commands and aliases through feature hooks.
- Feature packages gained clearer internal boundaries and compatibility re-exports while old core wiring was removed.
- Smoke tests now cover command dispatch arity and full-stack command execution; the test runner was standardized on pytest.

### Fixed

- Broken command wrappers, missing aliases, stale imports, dead code, and feature-loader wiring issues were cleaned up during the package extraction.

### Tests

- The `v1.6.0` tag passed **163 tests** with `pytest -q`.

---

## 1.5.0 (2026-05-29)

### Added

- **Reminder overhaul**: reminders gained permanent event IDs, configurable lead-time schedules, holiday alignment, a reminder editor, and a tomorrow preview in the header.
- **Birthday manager**: birthdays can be listed, added, deleted, and assigned reminder levels; `bd` accepts an optional reminder level.
- **Hijri event**: added the Martyrdom of Muslim ibn Aqil (AS).
- **Weather translation** for thunderstorms.
- **Test isolation**: `DAILYDRIVER_DB` makes the database path configurable, and the test runner uses a temporary database.

### Changed

- Command handlers were unified around the raw command line, and shared post-handler logic now prevents duplicate header redisplays.
- Birthday and calendar displays gained schedule-aware rendering, separate birthday lines, dynamic columns, wrapped names, duplicate suppression, and improved holiday alignment.
- Modern cultural figures were removed from the Jalali events, the Eid al-Adha title was updated, and Python 3.10 became the minimum supported version.

### Fixed

- Clean-clone test failures, the quit path, and related database/path issues were fixed.

### Tests

- The `v1.5.0` tag passed **161 tests** with `pytest -q`.

---

## 1.4.0 (2026-05-21)

### Added

- **Unified time-expression parser**: all journal, sleep, nap, and prayer input supports clock times, ranges, `l`/`last`, `n`/`now`, durations, offsets, and AM/PM disambiguation.
- **Header redesign**: modern centered date block, Jalali/Gregorian/Hijri dates, fixed-width prayer placeholders, combined sleep/nap line, birthday countdowns, a compact bottom bar, and section separators.
- **`recent` command**: renamed from `last` and aligned with `view` and `search`.
- **Test and tooling expansion**: parser, logger, calendar, Hijri, hygiene, prayer backlog, terminal, and multiline tests, plus Ruff, Black, and isort configuration.

### Changed

- Event commands now use a consistent operation, header refresh, and confirmation order.
- Sleep and nap commands share the unified parser and support chained ranges such as `s l-9`, `s 23-n`, `s ln`, and `nap l--5` without interactive time prompts.
- `p -15` uses the shared parser to log a prayer fifteen minutes before the relevant time.
- `ege` works correctly in multiline mode, and explicit time choices no longer receive redundant confirmation.
- The obsolete `date_str` header field and top-border code were removed.

### Fixed

- Journal timestamp conversion, FTS synchronization, import errors, unused code, and parser edge cases were corrected.

### Tests

- The release documentation recorded **148 tests** for `v1.4.0`; later tags are the first historical versions revalidated successfully in the current clean test environment.

---

## 1.3.0 (2026-05-13)

### Added

- **Database-backed state**: last-action, pending, and great-event state moved from dot-files into the `meta` table through migration v10.
- **Command modules**: `cli/commands/` and a clean dispatcher replaced the monolithic commander module.
- **Built-in aliases**: `pray`, `sleep`, `h`, and `qada` map to their primary commands.
- **Global Hijri offset**: `data/hijri_offset.txt` and the interactive `hijri` command apply a configurable correction to Hijri events and invalidate the cache immediately.
- **Terminal UI polish**: colored prayer nudges, calendar today highlighting, dimmed past-day headers, bold navigation prompts, search highlighting, and soft-wrapped event lines.
- **Calendar and weather additions**: Dahw al-Ard and dusty/blowing-dust translations.
- **Expanded tests** for the modular header, DB-backed state, dispatcher, and event commands.

### Changed

- Header assembly was split into domain-specific modules, and `is_past` became the clearer `is_today` state.
- Markdown became the default export format, with formatted tables, emojis, and day separators; `--txt` remains available.
- Prayer backlog commands `rq` and `mp` were replaced by `p q`, with flexible times, smart overdue detection, and an auto-advancing completion marker.
- ANSI-aware width calculation was added to wrapping, spreading, and header centering.

### Fixed

- Database-backed state helpers now commit reliably, FTS indexes stay synchronized, search scoring was corrected, and calendar event slot comparisons use Gregorian dates.

---

## 1.2.0 (2026-05-08)

### Added

- **Weather integration**: Tehran weather is scraped from IRIMO, cached hourly, and displayed with an offline fallback, temperature, condition emoji, and timestamp. Past-day views use cached weather.
- **`day` / `today`**: browse past days with navigation or direct Jalali dates; headers adapt to the selected day, and `d <id>` jumps from `view` or `search` to an entry's day.
- **Per-calendar icons**: Jalali, Gregorian, and Hijri icons plus holiday confetti now appear consistently across the header and calendar views.
- **Multi-page navigation**: `view` and `search` accept `n`/`p` with optional counts such as `5n`.

### Changed

- Search ranking uses stronger FTS scoring, exact-word and category boosts, and an OR-based LIKE fallback.
- Existing keywords were stemmed through migration v5, `pending_keywords` was removed, and keyword counts were added for TF-IDF.
- Sleep durations and weekday labels were repositioned in the header, and the bottom bar is also shown for past days.

### Fixed

- Compatibility for optional `cge` arguments, event-editor deletion persistence, cancelled-event handling, nap exports, prayer exports, and search/view pagination.

---

## 1.1.0 (2026-05-05)

### Added

- **Full-text search** using SQLite FTS5 with LIKE fallback, relevance ranking, and fuzzy boosts for time of day, relative dates, and categories.
- **Nap logging** with start time, duration, and optional description, including header, summary, and export support.
- **Keyword editor** for reviewing keywords and managing stopwords.
- **Porter2 stemming** and a morphological tokenizer for plurals, possessives, contractions, hyphenated words, and cleaned query tokens.
- **Database migrations** for the initial schema, naps, FTS, and keyword changes.

### Changed

- Keyword learning moved to TF-IDF with an exact-path boost and search uses OR matching for forgiving multi-word queries.
- Calendar event display uses English titles while retaining Persian titles in the data.
- The event editor saves deletions immediately, and the entry viewer displays Jalali dates.

### Fixed

- Cancelled great-event logging, optional `cge` arguments, `last X mins` parsing, and search/view import and pagination issues.

### Dependencies

- Added `porter2stemmer` to the runtime dependencies.

---

## 1.0.0 (2026-05-02)

This first public release consolidated the foundational development from April 24 through May 2.

### Added

- **Core application**: modular `dailydriver/` package, SQLite persistence, terminal REPL, single-command execution, keyboard help, and local runtime paths.
- **Prayer and sleep logging**: prayer slot selection, exact time confirmation, jamaat and shak flags, dynamic Tehran prayer times, sleep duration calculation, compact ranges, and overdue-prayer commands.
- **Journal workflow**: free-text entries with relative time parsing, multiline mode, categories, flags, automatic keyword learning, filtered views, chaining, and event timestamps.
- **Events and reminders**: great events, running events, chained entries, intentions, hygiene intervals and header nudges, birthdays, and upcoming reminders.
- **Calendars**: Jalali, Gregorian, and Hijri event data with month and responsive year views.
- **Statistics and summaries**: prayer adherence, sleep averages, hygiene, category statistics, and the `today` view.
- **Export and editing tools**: human-readable exports for prayers, sleep, and entries plus the mobile event editor.
- **Packaging and documentation**: `pyproject.toml`, MIT license, README, command reference, contributing guide, and dependency installation instructions.

### Changed

- Prayer times use monthly interpolation instead of the original fixed constants.
- State files, the database, and event data were moved under `data/`, with separate Jalali, Gregorian, and Hijri event files.
- The command reference was split out of `README.md`.

### Fixed

- Cancelled great-event logging preserves the event, imports and paths work from clean installations, and calendar events render one per header line.

### Dependencies

```bash
pip install jdatetime hijridate
```
