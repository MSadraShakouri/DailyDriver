# Export — `export`

Export a single, chronological timeline where journal entries, sleep, naps,
prayers, qada progress, and target logs are interleaved naturally by time and
grouped by day.

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

- **Markdown (default)** — journal-style bullets, times, and quoted details.
- **Plain text (`--txt`)** — the same timeline without Markdown formatting.

Each feature contributes its own timeline items through the `export_items` hook
(see [Architecture](../architecture.md)), so the export stays complete as
features are added.

## Void export

The void scratchpad is exported separately with `vexport` — see
[Logging](logging.md#void-scratchpad--v-alias-void-vexport).
