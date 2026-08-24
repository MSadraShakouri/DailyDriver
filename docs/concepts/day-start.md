# Day Start Hour

By default, DailyDriver treats the day as starting at **4:00 AM** rather than
midnight. This matters because entries logged in the small hours (say, a 2 AM
hygiene log or target progress) usually belong to the *previous* day in how you
think about your routine.

## What it affects

The day-start hour is applied to:

- **Hygiene** — nudges and the manager: an entry before the day-start hour
  counts toward the previous day.
- **Targets** — daily totals and interval calculations use the shifted day.

Other views (journal timestamps, calendars) use the real calendar date.

## Changing it

| Usage | Meaning |
|-------|---------|
| `daystart` | Show the current day-start hour |
| `daystart <0-23>` | Set the day-start hour |

Set it to `0` for a plain midnight boundary, or later (e.g. `5`) if your day
starts later. See [Tools & Setup](../commands/tools.md#day-start-hour--daystart).
