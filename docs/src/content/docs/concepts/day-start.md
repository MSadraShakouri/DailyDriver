---
title: "Day Start Hour"
---

By default, DailyDriver treats the day as starting at **4:00 AM** rather than
midnight. This matters because entries logged in the small hours (say, a 2 AM
hygiene log or target progress) usually belong to the *previous* day in how you
think about your routine.

## What it affects

The day-start hour is applied to:

- **Hygiene** — nudges and the manager: an entry before the day-start hour
  counts toward the previous day.
- **Targets** — daily totals and interval calculations use the shifted day.
- **Day view (optional)** — the `day` timeline has two boundary modes,
  toggled with `m` inside the view: **midnight** (the default, 00:00 → 24:00)
  and **day start**, which runs from the day-start hour to the same hour the
  next day. The last-used mode is remembered.

Other views (journal timestamps, calendars, export) use the real calendar
date.

## Changing it

| Usage | Meaning |
|-------|---------|
| `daystart` | Show the current day-start hour |
| `daystart <0-23>` | Set the day-start hour |

Set it to `0` for a plain midnight boundary, or later (e.g. `5`) if your day
starts later. See [Tools & Setup](../commands/tools.md#day-start-hour--daystart).
