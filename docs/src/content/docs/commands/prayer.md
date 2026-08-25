---
title: "Prayer"
---

## Log a prayer — `p` (alias `pray`)

Logs a prayer for the current (or specified) slot. Pressing Enter confirms.
Prayer times are interpolated for Tehran from monthly data.

| Usage | Meaning |
|-------|---------|
| `p` | Log the current slot (auto-guessed from the time) |
| `p -15` | 15 minutes before the fixed prayer time |
| `p 05:30` | Explicitly at 05:30 (slot guessed from the hour) |
| `p j` | With jamaat (no location) |
| `p j masjid` | With jamaat at a given location |
| `p s 3` | With a shak (doubt) count of 3 |

Offsets and times use the shared
[time-expression syntax](../concepts/time-expressions.md).

## Backlog / qada marking — `p q`

Mark a past, unlogged prayer as qada. By default it logs at the **current**
time, which is the natural choice for catching up.

| Usage | Meaning |
|-------|---------|
| `p q` | Mark a past unlogged prayer as qada (logs at current time) |
| `p q -15` | Mark with a time of 15 minutes ago |
| `p q 03:11` | Mark at 03:11 on the past date |

> `p q` is the quick per-prayer catch-up. For managing a standing backlog of
> missed prayers and fasting over time, use the [`qada` manager](qada.md).

## Travel mode

In [travel mode](tools.md#travel-mode-travel), `p` shows a smart slot selector
instead of assuming Tehran times, and location-dependent prayer nudges are
suppressed.
