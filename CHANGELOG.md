# Changelog

## v2.1.0 (2026‑05‑02)

### Added
- `cal` command: clean Unix‑style month grid.
- `year` command: responsive full‑year calendar with holiday list.
- `export` command: export sleep, prayers, and entries to a human‑readable file.
- Reminder feature: events with `remind: true` appear in the header two weeks ahead.
- Three‑calendar event system (Jalali, Gregorian, Hijri) with dynamic conversion.
- Dynamic prayer times for Tehran (monthly interpolation from official data).
- `hijridate` dependency for Hijri date conversions.
- Mobile‑friendly event editor (tools/edit_events.py).

### Changed
- Prayer times now interpolated monthly instead of fixed constants.
- README updated with new commands and project structure.

### Fixed
- `ege` now preserves the great event when logging is cancelled.

---

## v2.0.0 (2026‑04‑29)

### Added
- Complete modular restructure into `dailydriver/` package.
- Split `prayer.py`, `logger.py`, `parser.py`, `database.py` into focused modules.
- Great‑event commands (`sge`, `ege`, `cge`).
- Chaining command (`ln`).

### Changed
- All imports updated to use the new package structure.
- State files and database moved to `data/` directory.
- `main.py` is now a thin entry point that calls `dailydriver.cli.commander`.

### Removed
- Dead flags system (`flag` command, tables dropped).

---

## v1.0.0 (2025)
- Initial release: prayer, sleep, journal, hygiene, birthday, intention tracking.