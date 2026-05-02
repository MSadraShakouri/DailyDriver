# Changelog

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
