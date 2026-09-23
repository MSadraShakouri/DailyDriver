# City

`city` opens one interactive manager that controls **where you are**: the default city, a weekly schedule of city rules, and a temporary override. Prayer times and the weather line follow the resolved city automatically.

## The manager

| Screen | What it shows |
|--------|---------------|
| Current city | e.g. `Karaj (override until Tue 08:00)`, `Tehran (schedule, until 18:00)`, or `Tehran (default)` |
| Upcoming transitions | The next rule starts (up to five) |

Options: **change city now**, **edit schedule**, **edit default**, **view/clear override**, quit. There are no subcommands — everything is interactive.

## Change city now

One concept, one action: *set city X until Y*, where Y is:

| Duration | Behaviour |
|----------|-----------|
| **Next schedule change** | Clears at the next rule start (shown in the menu). With no rules it stays until cleared. |
| **Specific date & time** | Clears at that timestamp. Afterwards the schedule governs if a rule exists at that moment, otherwise the default — nothing lingers. |
| **Indefinite** | Persists until you clear it under *view/clear override*. |

Picking *use the default city* stores an override whose city is *default*: the schedule is suspended and the default city applies until the chosen duration ends.

## Weekly schedule

Rules map weekday **time windows to cities**. Validation happens on save:

- **Overlap** on a shared weekday is rejected.
- **Adjacent** rules are fine — `08:00–12:00 Karaj` then `12:00–20:00 Tehran` hands over at 12:00 exactly (ranges are inclusive at the start, exclusive at the end).
- **Gaps** are fine too — outside any rule the [default city](#edit-default) applies.
- No overnight windows (`from` must be earlier than `to` within one day).
- Edits take effect immediately; the next header render uses them.

Days use the Iranian week: `0 = Sat … 6 = Fri`, and `all` covers the week.

## Edit default

Pick any city from the registry. The default is required and falls back to Tehran when unset.

## Registry

Cities live in the version-controlled [`data/cities.json`](https://github.com/MSadraShakouri/DailyDriver/blob/main/data/cities.json) — each entry carries coordinates (used by the offline prayer calculation) and an IRIMO weather page URL (cities without one simply get no weather line). Adding a city is a file edit; there is no runtime mutation. See [Cities](../concepts/cities.md) for the resolution rules.

## Travel mode

[Travel mode](tools.md#travel-mode--travel) wins completely: no city resolution runs, and weather and prayer nudges are suppressed as usual.
