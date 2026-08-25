---
title: "Calendar"
---

DailyDriver understands three calendars at once — Jalali (Persian), Gregorian,
and Hijri — each with its own icon (🔆 Jalali, 🌐 Gregorian, 🌙 Hijri) and
holiday confetti (🎊). See [Calendars](../../concepts/calendars/) for the model.

## Month grid — `cal`

| Usage | Meaning |
|-------|---------|
| `cal` | Current month, today highlighted |
| `cal 6` | Month 6 (Shahrivar) of the current year |
| `cal 6 1405` | Month 6 of year 1405 |

The grid follows the Unix `cal` style with a Saturday–Friday week. Upcoming
events are listed below the grid.

## Year grid — `year`

Displays the full Jalali year as a responsive multi-column grid (1, 2, or 3
months per row depending on terminal width). Today is shown in reverse video in
its month, and official holidays are listed below.

## Hijri offset — `hijri`

Always interactive. Opens a selector to apply a correction (-2 to +2 days) to
Hijri date conversion, for moon-sighting differences. The chosen offset is
stored in the version-controlled `data/hijri_offset.txt` and applied to all
Hijri events immediately.

| Usage | Meaning |
|-------|---------|
| `hijri` | Show today's Hijri date with offsets and pick one |
