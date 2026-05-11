# Optimizations & Improvements

Ideas for making DailyDriver faster, cleaner, and more maintainable.

---

## 🔴 High Priority (immediate impact, low risk)

### Move state files into the database
- Currently `.daily_last_action`, `.daily_pending`, and `.daily_great_event` are separate files.
- Move them into the `meta` table (like `prayer_complete_until`).
- **Effort:** Small migration + small changes in `logger.py`.  
  **Benefit:** Fewer disk operations, all state in one place, no hidden dotfiles.

### Enable SQLite WAL mode
- One‑line change: `PRAGMA journal_mode=WAL;` after opening the DB.
- Write‑Ahead Logging makes writes faster and reduces locking, even for a single‑user app.
- **Effort:** One line in `database.py`.  
  **Benefit:** Slightly faster writes, safer file handling.

---

## 🟡 Medium Priority (add when convenient)

### Smarter `_update_complete_until`
- After logging a qada far in the past, avoid scanning all intermediate days.
- Check only if the logged date is now complete, then advance only as far as contiguous completed dates go.
- **Effort:** Small. **Benefit:** Faster after large backlog catches up.

### Cache weather condition translations in memory
- `weather_conditions.json` is loaded from disk every time a condition is translated.
- Load it once at module level and reuse the dictionary.
- **Effort:** Tiny. **Benefit:** Slightly faster header, cleaner code.

### Reduce database queries in header
- Several queries can be combined or cached (e.g., prayer slot lookups, birthday checks).
- Consider single‑query fetches where possible to reduce round‑trips.
- **Effort:** Medium. **Benefit:** Snappier header, especially on Termux.

### Add pagination to `p q` backlog list
- Currently shows **all** unlogged slots at once.
- Add `n`/`p`/`q` navigation (like `view` and `search`).
- **Effort:** Small. **Benefit:** Cleaner UI for long backlogs.

### Expand test coverage
- Missing tests for: backlog logic, export formatting, `is_today` refactor, weather fallback.
- Focus on `prayer_backlog.py` and `export_log.py` (most recent changes).
- **Effort:** Medium. **Benefit:** Prevent regressions.

---

## 🟢 Low Priority (nice to have, no urgency)

### Add dispatch comments in commander.py
- Add `# prayer_log.py`, `# sleep.py`, etc. next to each handler in `make_dispatch()`.
- **Effort:** Tiny. **Benefit:** Easier navigation.

### Pre-compile regex patterns
- Move frequently used regexes (time parsing, `@` tagging) to module‑level `re.compile()`.
- **Effort:** Tiny. **Benefit:** Micro‑optimization, cleaner code.

### Terminal width reactive layout (basic colour/format done)
- Basic ANSI‑aware display, bold prompts, dimmed dates, and wrapped lines are already in place.
- Further improvements: auto‑collapse header on very narrow screens (<60 cols), drop weekday prefix, etc.
- **Effort:** Small. **Benefit:** Better mobile/Termux experience.

### Lazy‑load calendar event JSON files
- Currently all three event files are loaded when the module is first imported.
- Defer loading until `get_events()` is actually called.
- **Effort:** Small refactor in `calendar_events.py`.  
  **Benefit:** Faster startup for quick commands that don’t touch the calendar.

### Threaded weather fetch
- Fetch weather in background thread (with timeout) to avoid blocking startup.
- Current `_fetch_failed_this_session` flag is a good stopgap.
- **Effort:** Medium. **Benefit:** Startup never hangs on slow network.

### Periodic VACUUM / DB health check
- Over many months, the DB can become fragmented.
- Show DB size in `stats` and optionally run `VACUUM` when size exceeds a threshold.
- **Effort:** Small. **Benefit:** Long‑term health, keeps backup sizes small.

### Prune old weather_log rows (optional)
- The table grows by one row per successful fetch.
- Could add a `weather prune` command to keep only the most recent N days of history.
- **User preference:** may want to keep full history for future analysis; feature can be added later.
- **Effort:** Tiny. **Benefit:** Keeps DB slim on devices with limited storage.

### Extract calendar event loaders
- `calendar_events.py` has a single `_convert_all_events` handling three calendars.
- Split into `_load_jalali_events`, `_load_gregorian_events`, `_load_hijri_events` for readability.
- **Effort:** Small. **Benefit:** Easier to maintain.

### Future city support for prayer times
- `prayer_times.py` has hardcoded Tehran data.
- When adding cities, swap `_DATA` dict for a JSON file keyed by city name.
- **Effort:** Deferred. **Benefit:** Clean multi‑city support.

### Review EXPLAIN QUERY PLAN on slow queries
- Run `EXPLAIN QUERY PLAN` on header queries.
- Add indexes if needed (e.g., `prayer_logs(jalali_date, prayer_slot)` for backlog scanning).
- **Effort:** Tiny. **Benefit:** Prevents future slowness.
