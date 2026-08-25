# Viewing & Summaries

## Day view — `day` (alias `today`)

Show a full day: the header adapts to that date (prayers, sleep, weather,
events) and the body is a unified chronological timeline of everything logged
that day — journal entries, prayers (🕌), sleep (💤), naps (😴), qada progress
(📿), and target logs (🎯). Journal entries appear as their category list
(without the `journal/` prefix), with the description underneath, and show a
time range (`HH:MM → HH:MM (dur)`) when a duration was logged.

| Usage | Meaning |
|-------|---------|
| `day` | Today |
| `day -1` | Yesterday |
| `day 1405-02-15` | A specific Jalali date |

Inside the view: `p`/`n` for previous/next day, `5n`/`5p` to jump multiple days,
type a `YYYY-MM-DD` date to go there, `q` to quit. From `view` or `search`,
`d <id>` opens the day of that entry.

`m` toggles the day boundary between two modes (persisted across sessions,
default **midnight**):

- **midnight** — the day runs 00:00 → 24:00;
- **day start** — the day runs from the configured day-start hour (see
  `daystart`, default 04:00) to the same hour the next day, so late-night
  activity counts toward the evening's day.

Items are placed on a day by their start time (falling back to log time),
the same rule `export` uses. Prayers and sleep also appear summarized in the
header; the timeline shows them in chronological context.

## Browse entries — `view`

| Usage | Meaning |
|-------|---------|
| `view` | All entries, newest first (by start time) |
| `view <filter>` | Filter by category text (e.g. `view project`) |

Entries with a logged duration show the full time range in export's format:
`YYYY-MM-DD HH:MM → HH:MM (dur)`; otherwise just the start time.

Inside: `n`/`p` (or `5n`/`5p`) to page, type an entry ID to edit it, `d <id>` to
open that entry's day, `q` to quit.

## Search — `search`

A simple filter over journal descriptions and category paths — no relevance
scoring. Query words are tokenized the same way journal keywords are (words
under 3 letters and stopwords are dropped, and the header reports them as
ignored). A word matches an entry when its stem equals the stem of a whole
word in the description or the category path — so `art` never matches
"start", while `meetings` finds "meeting".

| Usage | Meaning |
|-------|---------|
| `search programming` | Entries containing "programming" |
| `search python project` | Entries containing either word, best matches first |

Results are grouped by how many query words matched: entries with **all**
words first, then one fewer, and so on. Within each group entries are newest
first (by start time). Each group has a header like
`── All 3 terms (12 entries) ──`; when a page starts mid-group the header is
repeated with `cont.`. Entries with a logged duration show the export-style
time range `HH:MM → HH:MM (dur)`.

Results paginate with `n`/`p`/`5n`; matching words are highlighted in both the
description and the categories. Type an entry ID to edit, `d <id>` to open its
day, `q` to quit.

## Recent — `recent`

Shows the last 5 journal entries in the same wrapped layout as `view` and
`search`.

## Statistics — `stats`

A summary of:

- Prayer on-time / qada / missed counts and percentages (last 30 days)
- Sleep average, best, and worst (last 14 days)
- Hygiene adherence (logs vs expected)
- Top categories (last 30 days)
