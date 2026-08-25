---
title: "Calendars"
---

DailyDriver is calendar-aware in three systems simultaneously:

- 🔆 **Jalali** (Persian solar) — the primary calendar for dates and navigation.
- 🌐 **Gregorian** — shown alongside, and used for weather/prayer comparisons.
- 🌙 **Hijri** (Islamic lunar) — for religious dates and events.

## Events

Events live in three JSON files under `data/` (`events_jalali.json`,
`events_gregorian.json`, `events_hijri.json`). Each event carries an English
title (`title_en`) with the Persian preserved (`title_fa`). Holidays are marked
and rendered with confetti (🎊). Events appear in the header, `cal`, and `year`
views, with duplicate suppression when an event already shows as a today/tomorrow
reminder.

## Reminders

Calendar events and birthdays support reminder levels (0/1/2) with configurable
lead-time schedules, so upcoming items appear in the header ahead of time.
Important items use a more frequent schedule. Reminder data is stored per event
(`event_reminders`) and per birthday (`birthdays.remind_level`).

## Hijri offset

Lunar dates depend on moon sighting and can differ by a day or two between
sources. The `hijri` command applies a global correction (-2 to +2 days), stored
in the version-controlled `data/hijri_offset.txt` and applied to all Hijri
events immediately. See [Calendar commands](../commands/calendar.md#hijri-offset--hijri).
