# Calendars

DailyDriver is calendar-aware in three systems simultaneously:

- 🔆 **Jalali** (Persian solar) — the primary calendar for dates and navigation.
- 🌐 **Gregorian** — shown alongside, and used for weather/prayer comparisons.
- 🌙 **Hijri** (Islamic lunar) — for religious dates and events.

## Events

Events live in three JSON files under `data/` (`events_jalali.json`, `events_gregorian.json`, `events_hijri.json`). Each event carries an English title (`title_en`) with the Persian preserved (`title_fa`). Holidays are marked and rendered with confetti (🎊). Events appear in the header, `cal`, and `year` views, with duplicate suppression when an event already shows as a today/tomorrow reminder.

## Reminders

Calendar events and birthdays support reminder levels (0/1/2) with configurable lead-time schedules, so upcoming items appear in the header ahead of time. Important items use a more frequent schedule. Reminder data is stored per event (`event_reminders`) and per birthday (`birthdays.remind_level`).

## Hijri model and manual corrections

DailyDriver uses an offline Iranian-first month-start table. Confirmed or curated Iranian month starts are stored in `data/hijri_iran.json`; its `future_policy` metadata marks rows after the maintained horizon as provisional until an official announcement is available. Dates outside that table use a bundled calculated fallback, so the app does not need a Hijri conversion package at runtime. A scheduled workflow refreshes the table into a reviewable pull request.

The `hijri` command remains available for a newly announced discrepancy. Its `-2` to `+2` correction is stored for the current Hijri month in `data/hijri_overrides.json`, so correcting one month does not permanently shift every later month. Older global settings in `data/hijri_offset.txt` remain supported as a compatibility fallback. See [Calendar commands](../commands/calendar.md#hijri-offset--hijri).
