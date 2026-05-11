# Optimizations & Improvements

Ideas for making DailyDriver faster, cleaner, and more maintainable.

---

## 🔴 High Priority (immediate impact, low risk)

### Split header.py into smaller helper functions
- `build_header_data()` is over 270 lines.
- Extract: `_get_prayer_status`, `_get_sleep_and_naps`, `_get_birthdays`, `_get_hygiene_nudges`, `_get_events_and_reminders`, `_get_weather`, `_get_prayer_nudges`.
- **Effort:** Medium. **Benefit:** Easier testing, maintenance, and future changes.

### Reduce database queries in header
- Several queries can be combined or cached (e.g., prayer slot lookups, birthday checks).
- Consider single-query fetches where possible to reduce round-trips.
- **Effort:** Medium. **Benefit:** Snappier header, especially on Termux.

---

## 🟡 Medium Priority (add when convenient)

### Add pagination to `p q` backlog list
- Currently shows **all** unlogged slots at once.
- Add `n`/`p`/`q` navigation (like `view` and `search`).
- **Effort:** Small. **Benefit:** Cleaner UI for long backlogs.

### Expand test coverage
- Missing tests for: backlog logic, export formatting, `is_today` refactor, weather fallback.
- Focus on `prayer_backlog.py` and `export_log.py` (most recent changes).
- **Effort:** Medium. **Benefit:** Prevent regressions.

### Smarter `_update_complete_until`
- After logging a qada far in the past, avoid scanning all intermediate days.
- Check only if the logged date is now complete, then advance `complete_until` only as far as contiguous completed dates go.
- **Effort:** Small. **Benefit:** Faster after large backlog catches up.

### Add startup cache for expensive computations
- Cache daily prayer times (in memory, invalidate on date change).
- Cache keyword categories (invalidate when new keywords learned).
- **Effort:** Small. **Benefit:** Slightly faster REPL startup.

---

## 🟢 Low Priority (nice to have, no urgency)

### Pre-compile regex patterns
- Move frequently used regexes (time parsing, `@` tagging) to module-level `re.compile()`.
- **Effort:** Tiny. **Benefit:** Micro-optimization, cleaner code.

### Terminal width reactive layout
- Collapse header gracefully on narrow screens (<60 cols).
- Drop weekday prefix, abbreviate prayer labels further, wrap lines instead of truncating.
- **Effort:** Small. **Benefit:** Better mobile/Termux experience.

### Threaded weather fetch
- Fetch weather in background thread (with timeout) to avoid blocking startup.
- Current `_fetch_failed_this_session` flag is a good stopgap.
- **Effort:** Medium. **Benefit:** Startup never hangs on slow network.

### Add dispatch comments in commander.py
- Add `# prayer_log.py`, `# sleep.py`, etc. next to each handler in `make_dispatch()`.
- **Effort:** Tiny. **Benefit:** Easier navigation.

### Move safe inline imports to top
- Already mostly done. Double-check: `from dailydriver.domains.prayer_backlog import log_qada` in `prayer_log.py` may be safe to move to top (no circular import in practice).
- **Effort:** Tiny. **Benefit:** Cleaner code.

### Split export_log.py when next format is added
- Current file (326 lines) has `_to_markdown`, `_to_text`, and main logic.
- Extract format functions to `cli/export_formats.py` when adding JSON, CSV, etc.
- **Effort:** Deferred. **Benefit:** Avoids bloating the file further.

### Extract calendar event loaders
- `calendar_events.py` has a single `_convert_all_events` handling three calendars.
- Split into `_load_jalali_events`, `_load_gregorian_events`, `_load_hijri_events` for readability.
- **Effort:** Small. **Benefit:** Easier to maintain.

### Future city support for prayer times
- `prayer_times.py` has hardcoded Tehran data.
- When adding cities, swap `_DATA` dict for a JSON file keyed by city name.
- **Effort:** Deferred. **Benefit:** Clean multi-city support.

### Review EXPLAIN QUERY PLAN on slow queries
- Run `EXPLAIN QUERY PLAN` on header queries.
- Add indexes if needed (e.g., `prayer_logs(jalali_date, prayer_slot)` for backlog scanning).
- **Effort:** Tiny. **Benefit:** Prevents future slowness.

