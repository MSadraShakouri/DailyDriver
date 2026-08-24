# Viewing & Summaries

## Day view — `day` (alias `today`)

Show a full day, adapting the header to that date (prayers, sleep, weather,
events).

| Usage | Meaning |
|-------|---------|
| `day` | Today |
| `day -1` | Yesterday |
| `day 1405-02-15` | A specific Jalali date |

Inside the view: `p`/`n` for previous/next day, `5n`/`5p` to jump multiple days,
type a `YYYY-MM-DD` date to go there, `q` to quit. From `view` or `search`,
`d <id>` opens the day of that entry.

## Browse entries — `view`

| Usage | Meaning |
|-------|---------|
| `view` | All entries, newest first |
| `view <filter>` | Filter by category text (e.g. `view project`) |

Inside: `n`/`p` (or `5n`/`5p`) to page, type an entry ID to edit it, `d <id>` to
open that entry's day, `q` to quit.

## Search — `search`

Full-text search over descriptions and categories, with fuzzy scoring that
boosts time-of-day, relative dates, weekdays, month names (Jalali, Gregorian,
Hijri), and category matches. Uses SQLite FTS5 with a LIKE fallback, and
tolerates misspellings (`mornig` → morning).

| Usage | Meaning |
|-------|---------|
| `search programming` | Entries containing "programming" |
| `search morning` | Entries in the morning window (time boost) |
| `search yesterday` | Entries from the last few days (date boost) |
| `search monday` | Entries near the most recent Monday |
| `search programming night` | Combined text + time/category scoring |

Results paginate with `n`/`p`/`5n`; matches are highlighted. Type an entry ID to
edit, `d <id>` to open its day, `q` to quit.

## Recent — `recent`

Shows the last 5 journal entries in the same wrapped layout as `view` and
`search`.

## Statistics — `stats`

A summary of:

- Prayer on-time / qada / missed counts and percentages (last 30 days)
- Sleep average, best, and worst (last 14 days)
- Hygiene adherence (logs vs expected)
- Top categories (last 30 days)
