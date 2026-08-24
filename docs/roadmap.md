# Roadmap

This page tracks where DailyDriver has been and where it might go. The
**Shipped** section is drawn from real release history (`CHANGELOG.md` and the
`v1.4.0`–`v1.8.0` Git tags); nothing here is invented. The **Planned** section
collects ideas that are not yet built.

## Shipped

> Release tags are created manually (the `version` in `pyproject.toml` is just
> package metadata and does not create a git tag). After the v2.1.0 branch is
> merged, tag it: `git tag v2.1.0 <merge-commit> && git push origin v2.1.0`, or
> cut a GitHub Release named `v2.1.0`.

### ✅ v2.1.0 — 2026-08-24
- **Unified day timeline**: `day` shows everything logged that day in
  chronological order — journal entries, prayers, sleep, naps, qada, and
  targets — sharing one timeline builder with `export`; items are placed by
  start time. Each item renders as time, then label/categories, then the
  description.
- **Day-boundary modes**: `m` inside the day view toggles midnight
  (default) vs the configured day-start hour; the choice persists in the
  meta table.
- **Search rewritten as a token filter**: no relevance scoring; whole-word
  stem matching over descriptions and category paths, results grouped by how
  many query words matched (styled group headers, ignored-word reporting).
  The FTS/fuzzy scoring modules were removed.
- **Time ranges everywhere**: `view` and `search` show export's
  `HH:MM → HH:MM (dur)` format and sort/jump by start time.
- **Export polish**: day headers gain an abbreviated weekday
  (`Mon, 02 Shahrivar 1405`); the `export_items` hook accepts an optional
  inclusive end bound for future range export.
- **Category editor** (`tools/category_editor.py`, port 8768): list, rename,
  merge, and safe-delete categories, with a similar-pairs Suggestions tab.
- Fixed an ANSI-slicing bug in `pline_wrap` truncation; first test suites for
  search, day view, and the entry browser (499 tests).

### ✅ v2.0.0 — 2026-08-24
- Category ranking reworked: whole-segment path matching (no more `art`→`start`
  false positives) and a gentle, coverage-proportional exact-match boost where a
  full path match outranks a deeper partial one.
- prompt_toolkit input backend: command autocompletion, persistent history, and
  an autocompleting category picker (5 numbered suggestions, a 20-deep ranked
  live dropdown that removes already-chosen entries, Enter = suggestion #1) —
  with automatic fallback to plain input when non-interactive.
- `-h`/`--help` on every command from a single help registry; the `?` summary is
  generated from the same source.
- Birthday creation (`bd`) is now fully interactive; inline date parsing removed.
- Fixed the header event lines (great/running event) and the `ege`/`ee`
  cancelled-log behavior.
- **Breaking:** `bd` no longer accepts inline `name date` arguments.
- Documentation rebuilt into `docs/`; `COMMANDS.md` removed in favor of the new
  per-feature command pages.

### ✅ v1.8.0 — 2026-08-23
- Multiple sleep sessions per day; header shows total plus individual ranges.
- `tools/sleep_avg.py` sleep/nap analysis.
- Feature-package architecture overhaul: capability-based contracts
  (`NAME`, `VERSION`, `register_commands`, `header_sections`, `migrations`),
  monolithic `_logic.py`/`_header.py`/`_manager.py` files removed.
- Test suite rebuilt around package boundaries (395 passing tests).

### ✅ v1.7.0 — 2026-08-04
- **Breaking:** `qada` became a full feature (manager + `qada log`,
  `qada fasting`) instead of an alias for `p q`.
- Targets feature (`nazr`, `habit`, `targets`) with intervals, counters, and a
  manager.
- Travel mode; configurable day-start hour; void scratchpad; `u`/`update`;
  Termux dialog integration; hygiene manager overhaul.

### ✅ v1.6.0 — 2026-06-19
- Feature-package architecture introduced: 8 domains extracted into
  `dailydriver/features/` with standard hooks.
- Dispatcher unified on raw command-line strings; test suite overhaul (163
  tests).

### ✅ v1.5.0 — 2026-05-29
- Reminder overhaul: permanent event IDs, reminder levels, configurable
  schedules, visual reminder editor, tomorrow preview.
- Interactive birthday manager; test isolation via `DAILYDRIVER_DB`.

### ✅ v1.4.0 — 2026-05-21
- Unified time-expression language across journal, sleep, nap, and prayer.
- Header redesign; `recent` command; 120+ new tests (148 total).

### ✅ v1.3.0 — 2026-05-13
- State files moved into the database (`meta` table); commander split into
  command modules; built-in aliases; global Hijri offset with interactive
  `hijri`; terminal UI polish.

### ✅ v1.2.0 — 2026-05-08
- Weather integration (IRIMO, Tehran); `day`/`today` navigation; per-calendar
  icons; multi-page navigation in `view`/`search`.

### ✅ v1.1.0 — 2026-05-05
- Full-text search (FTS5) with fuzzy boosts; nap logging; keyword editor;
  stemming and a morphological tokenizer; TF-IDF + exact-path category boost.

### ✅ v1.0.0 — 2026-05-02
- First modular release: prayers, sleep, hygiene, birthdays, intentions, journal
  with keyword learning, events/chaining, stats, calendars, export, and the
  three-calendar event system.

## Planned

Ideas gathered from the former `TODO.md` and the code review notes. These are
candidates, not commitments, roughly grouped by priority.

### High priority
- **Export a date range** — `export YYYY-MM-DD YYYY-MM-DD` in addition to the
  current last-X-days form. The `export_items(conn, start, end=None)` hook
  already supports an upper bound; only the `export` command's argument
  parsing needs to change.

### Medium priority
- **Read-only entry view** from `view`/`search` (a separate `e`/`edit` key to
  enter the editor).
- **Quick-add templates** — one-word shortcuts expanding to a preset category
  and duration (e.g. `bath`).
- **Enhanced statistics** — words per entry, entries-per-day chart, chronotype
  histogram, sleep regularity, prayer-time distribution, category trends, year
  progress.
- **Recall command** — surface a random past entry (excluding e.g. `hygiene/*`).
- **Mood tracking** with occasional prompts.
- **Quick notes** — a scratchpad draft, saveable later.
- **Interactive in-app viewing** of past data (export-like but browsable).
- **`now` command** — one-shot status (next prayer, entry count, active great
  event), ideal for `da now`.
- **Reminders overhaul** — less noisy, importance-based schedules for birthdays
  and events.
- **Random fun stats** — an occasional record/highlight.

### Low priority
- Daily quote / hadith; prayer times and weather for other cities; extra weather
  fields; keyword editor showing the original unstemmed word.
- **Undo**, **CSV export**, and a **backup** command (from the review notes).

### Infrastructure
- **Wiki sync** — a GitHub Actions workflow to publish `docs/` to the GitHub
  Wiki. See [WIKI-SYNC.md](WIKI-SYNC.md).

Performance and cleanup ideas live in
[reference/optimizations.md](reference/optimizations.md).
