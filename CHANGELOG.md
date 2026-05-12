# Changelog

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
