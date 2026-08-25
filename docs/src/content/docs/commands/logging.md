---
title: "Logging"
---

The everyday, muscle-memory commands. These keep their fast inline syntax — you
type the whole thing on one line. All times use the shared
[time-expression syntax](../../concepts/time-expressions/).

## Journal entries (free text)

Anything not recognized as a command is a journal entry. The flow is:

1. Time expressions in the text are parsed and confirmed.
2. Categories are suggested (see [Categories](../../concepts/categories/)); you
   pick one or more, or type a new path.
3. The entry is saved.

```
> read Quran for 30 minutes
> worked on the project from 9-12
> last Thursday visited grandmother
```

If a great event is active and suggestions are shown, the picker also offers
`0 = Great Event only`.

### Category selection

When suggestions exist, a short numbered list is shown in ranked order (best
match first). In an interactive terminal the picker also autocompletes as you
type, with a live dropdown that drops categories you've already picked (by name
or by number). Press Tab to complete, space-separate to choose several, or type
a brand-new path. Press **Enter alone to accept suggestion #1**; type `0` for
"Great Event only" when a great event is active. See
[Categories & Keyword Learning](../../concepts/categories/) for how the ranking
and selection work.

## Sleep — `s` (alias `sleep`)

Log a sleep session with bed and wake time.

| Usage | Meaning |
|-------|---------|
| `s 23:00 07:15` | Sleep at 23:00, wake at 07:15 |
| `s 23-7:15` | Compact sleep-wake form |
| `s n 08:00` | `n` = now (fell asleep now) |
| `s -30 08:00` | Fell asleep 30 minutes ago |
| `s l-9` | From last action to 09:00 |
| `s 23-n` | From 23:00 to now |
| `s ln` | From last action to now |
| `s l--10` | From last action to 10 minutes ago |

Multiple sleep sessions per day are allowed; the header shows the total duration
and each individual range.

## Naps — `nap`

Same input style as sleep, for short daytime sleeps.

| Usage | Meaning |
|-------|---------|
| `nap 14:00 14:25` | Nap between two times |
| `nap 14-14:25` | Compact form |
| `nap l-14:00` | From last action to 14:00 |
| `nap l--5` | From last action to 5 minutes ago |

Typing `nap` alone prints usage. Naps appear as total nap time in the header and
in the day summary.

## Void scratchpad — `v` (alias `void`), `vexport`

A private scratchpad completely separate from the journal: no time parsing, no
categories, no keyword learning, and it does **not** update `last_action` (so it
never interferes with chaining).

| Usage | Meaning |
|-------|---------|
| `v <text>` | Log a void entry |
| `void <text>` | Same, alias |
| `vexport <duration\|all>` | Export void entries to Markdown (e.g. `vexport 7d`) |
