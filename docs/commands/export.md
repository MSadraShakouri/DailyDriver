# Export — `export`

Export a single, chronological timeline where journal entries, sleep, naps,
prayers, qada progress, and target logs are interleaved naturally by time and
grouped by day. Day headers show the Jalali date with an abbreviated weekday
(derived from the Gregorian equivalent, like the app header), e.g.
`Mon, 02 Shahrivar 1405`.

| Usage | Meaning |
|-------|---------|
| `export 7d` | Last 7 days as a Markdown timeline (default) |
| `export 2w --txt` | Last 2 weeks as plain text |
| `export 3m` | Last 3 months |
| `export 1y` | Last 1 year |
| `export all` | Everything, no cutoff |

Durations use the same suffixes as elsewhere: `d` (days), `w` (weeks),
`m` (months), `y` (years).

## Formats

- **Markdown (default, or `--md`)** — journal-style bullets, times, and quoted details.
- **Plain text (`--txt`)** — the same timeline without Markdown formatting.

The result is written to `export_<duration>.md` (or `.txt`) in the current
directory.

Each feature contributes its own timeline items through the `export_items` hook
(see [Architecture](../architecture.md)), so the export stays complete as
features are added.

## Void export

The void scratchpad is exported separately with `vexport` — see
[Logging](logging.md#void-scratchpad--v-alias-void-vexport).
