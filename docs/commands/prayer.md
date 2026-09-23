# Prayer

## Log a prayer — `p` (alias `pray`)

Logs a prayer for the current (or specified) slot. Pressing Enter confirms. Prayer times are calculated offline for the [resolved city](../concepts/cities.md) from fixed coordinates and the University of Tehran solar-angle convention; the app makes no network request.

| Usage | Meaning |
|-------|---------|
| `p` | Log the current slot (auto-guessed from the time) |
| `p -15` | 15 minutes before the fixed prayer time |
| `p 05:30` | Explicitly at 05:30 (slot guessed from the hour) |
| `p j` | With jamaat (no location) |
| `p j masjid` | With jamaat at a given location |
| `p s 3` | With a shak (doubt) count of 3 |

Offsets and times use the shared [time-expression syntax](../concepts/time-expressions.md).

## Prayer window boundaries

Each merged slot opens at its adhan and runs to a fiqh deadline (Khamenei's risala):

| Slot | Window opens | فضیلت (green) ends | Deadline |
|------|--------------|--------------------|----------|
| Fajr | Fajr adhan (17.7°) | Eastern redness apparent (اسفار, −14°) | Sunrise |
| Dhuhr & Asr | Dhuhr adhan | Post-zuwal shadow equals the gnomon | Sunset |
| Maghrib & Isha | Maghrib adhan (4.5°) | Red twilight gone (زوال شفق, −14°) | Shar'i midnight (sunset → next Fajr midpoint) |

The header nudges follow the window: a yellow pre-alert during the last hour before it opens (`🕌 Fajr — in ~30 min`), then one single-colored `🕌 Fajr — until 06:10` line while it is open — **green** inside the فضیلت window, **yellow** for the gap, **red** for the final stretch (the last 30 minutes before sunrise; the last 2 hours before sunset or shar'i midnight) — and finally a red `⚠️ not logged` line after the deadline. Logged slots drop their line; past-day overdue nudges are unchanged.

## Backlog / qada marking — `p q`

Mark a past, unlogged prayer as qada. By default it logs at the **current** time, which is the natural choice for catching up.

| Usage | Meaning |
|-------|---------|
| `p q` | Mark a past unlogged prayer as qada (logs at current time) |
| `p q -15` | Mark with a time of 15 minutes ago |
| `p q 03:11` | Mark at 03:11 on the past date |

> `p q` is the quick per-prayer catch-up. For managing a standing backlog of missed prayers and fasting over time, use the [`qada` manager](qada.md).

## Travel mode

In [travel mode](tools.md#travel-mode--travel), `p` shows a smart slot selector instead of assuming Tehran times, and location-dependent prayer nudges are suppressed.
