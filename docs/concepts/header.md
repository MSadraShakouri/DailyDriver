# The Header

Every screen opens with the daily header — a compact dashboard of the current
(or viewed) day. It is assembled from each feature's `header_sections` hook, so
the content grows with the app. Sections are ordered by numeric priority (lower
renders first), not by feature order.

## What it shows

- **Date block** — a centered header with the Jalali weekday and date, a thin
  separator, and the Gregorian and Hijri dates.
- **Prayers** — the five daily prayers with status, color-coded overdue and
  pre-alert nudges (red = overdue, yellow = pre-alert).
- **Sleep & naps** — total sleep duration and ranges, plus total nap time.
- **Weather** — Tehran conditions with an emoji (IRIMO, cached hourly);
  suppressed in travel mode.
- **Birthdays** — upcoming birthdays with age and a countdown.
- **Hygiene** — nudges for overdue hygiene items.
- **Calendar events & reminders** — three-calendar events with per-calendar
  icons, holiday confetti, and a tomorrow preview.
- **Qada / target nudges** — overdue backlog and target reminders.

## Behavior

- On **past days**, the header adapts to that date and dims appropriately;
  time-sensitive nudges are constrained to today.
- Display width is **ANSI-aware**: color codes are stripped before measuring, so
  colored text never misaligns.
- Widths adapt to the terminal; resize to at least 80 columns for best results.

For how features contribute header content, see the `header_sections` hook in
[Architecture](../architecture.md) and `dailydriver/features/HOOKS.md`.
