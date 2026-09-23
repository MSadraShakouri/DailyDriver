# Cities

DailyDriver resolves **one active city** every time it needs a location: the prayer windows use its coordinates, and the weather line uses its IRIMO page. Resolution is pure infrastructure in `core/location/` — it is not a feature, cannot be disabled, and imports nothing from features (the same precedent as [events & chaining](../architecture.md)).

## Precedence

```text
travel  >  override  >  schedule  >  default
```

| Source | When it applies |
|--------|-----------------|
| **Travel** | Travel mode wins completely; no city resolution runs. |
| **Override** | Set from the [`city`](../commands/city.md) manager: one concept — *city X until next change / a timestamp / indefinitely*. `override_city = null` means *suspend the schedule and use the default*. Expired overrides are ignored (never linger): the schedule governs if a rule exists at that moment, otherwise the default. |
| **Schedule** | A weekly rule whose weekday window contains now. Inclusive start, exclusive end. |
| **Default** | The configured default city (Tehran until changed). |

`resolve_city(conn, now=None)` in `core/location/resolver.py` is the single entry point: a pure function returning the city plus *why* it won (`travel` / `override` / `schedule` / `default`) and an optional *until* hint (the current rule's end, or the override's expiry). The weather header uses the hint to render `(Karaj, until 18:00)` when a rule ends within two hours.

## Schedule semantics

- Rules live in the `city_rules` table; the active override and default live in the single-row `city_state` table (core migrations 14 and 15).
- Weekdays are the Iranian week: Saturday = 0 through Friday = 6.
- **Overlaps on a shared day are rejected at save time. Adjacent rules are valid; gaps fall through to the default city.**
- No overnight windows: a rule belongs to one calendar day.
- The resolver's "now" is **midnight-based** — the configured [day-start boundary](day-start.md) is a *view* concept and never shifts city rules.
- Schedule edits take effect immediately.

## Registry

`data/cities.json` is the version-controlled registry. One entry per city:

```json
"Karaj": {
  "lat": 35.8327,
  "lon": 50.9916,
  "tz": 3.5,
  "weather_url": "https://www.irimo.ir/far/wd/701-....html?id=17524"
}
```

- `lat`/`lon`/`tz` feed the offline solar calculation (the same University of Tehran angles for every city — 17.7° Fajr, 4.5° Maghrib; see [Prayer](../commands/prayer.md#prayer-window-boundaries)).
- `weather_url` is optional: cities without an IRIMO page still get prayer times, but no weather line.
- Adding a city is a file edit. No runtime mutation, no UI for the registry itself.

## What the city changes

- **Prayer**: window boundaries (Fajr/Dhuhr/Maghrib adhan times, sunrise/sunset, fadilat ends, shar'i midnight) are computed for the resolved city.
- **Weather**: fetched from the city's IRIMO page, cached **per city**, and displayed with the city suffix — `☀️ 32°C clear (Karaj) 14:30`.
- **Prayer deadline lines never show the city** — they stay short.
- Past-day weather display is unchanged by cities.
