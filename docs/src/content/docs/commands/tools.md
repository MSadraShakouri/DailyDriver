---
title: "Tools & Setup"
---

These are deliberate, less-frequent actions — creation, configuration, and
management. As of v2.0, creation/editing flows are **fully interactive**
(prompted and validated) rather than parsed from inline arguments.

## Birthdays — `bd`, `birthdays`

### Add a birthday — `bd`

`bd` is fully interactive. It prompts for each field in turn; any inline
arguments are ignored.

```
> bd
Name: Ali
Day (1-31): 12
Month (1-12): 5
Year (e.g., 1386, Enter=skip): 1386
Reminder level? (0=default, 1=important, Enter=0): 1
```

The year is optional (Enter to skip). Reminder level `1` marks the birthday as
important, which uses a more frequent reminder schedule.

### Manage the list — `birthdays`

Opens an interactive manager to list birthdays and toggle reminder levels, add,
or delete entries.

## Intentions — `t`

Lightweight to-dos with optional Jalali deadline and expected duration.

| Usage | Meaning |
|-------|---------|
| `t` | Interactive (prompts for deadline `YYYY/MM/DD` and duration) |
| `t <description>` | Quick add with a description only |

## Hygiene — `hygiene`

Define recurring hygiene items with intervals and get header nudges when
they're overdue. Log an entry under a matching category (e.g. `hygiene/shaving`)
to record the last time. The manager respects the
[day-start hour](../../concepts/day-start/).

Opens an interactive manager with a dynamic table sorted by urgency
(red = overdue, yellow = due today) and add/edit/delete flows.

## Travel mode — `travel`

Disable location-dependent features (weather, prayer nudges) while away from
Tehran. Prayer logging switches to a smart slot selector.

| Usage | Meaning |
|-------|---------|
| `travel` | Toggle travel mode |
| `travel on` | Enable |
| `travel off` | Disable |
| `travel status` | Show current state |

## Day start hour — `daystart`

Shift the day boundary used by hygiene and target calculations — and, when
the day view is switched to day-start mode (`m` inside `day`), the boundary
of the day timeline. Default is 4:00 AM, so before-dawn logs count toward the
previous day. See [Day Start Hour](../../concepts/day-start/).

| Usage | Meaning |
|-------|---------|
| `daystart` | Show the current day-start hour |
| `daystart <0-23>` | Set the day-start hour |
