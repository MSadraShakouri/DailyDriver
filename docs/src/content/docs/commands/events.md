---
title: "Events & Chaining"
---

DailyDriver has three complementary ways to capture time spent on activities.

## Running event — `se`, `ee`, `ce`

Fine-grained timing of a single activity you're doing right now.

| Command | Meaning |
|---------|---------|
| `se` | Start: save the current time as the event's start |
| `ee [text]` | End: stop the event and log an entry with optional description |
| `ce` | Cancel the running event without logging |

```
> se
  ... (do the thing) ...
> ee finished the report
```

## Chaining — `ln`

Log an entry spanning from your **last action** until now, without having
started a timer. Useful when you finish something and want to log it after the
fact.

| Command | Meaning |
|---------|---------|
| `ln [text]` | Log from `last_action` to now |

```
> ln replied to emails
```

The `last_action` timestamp is updated whenever you log something. You can also
refresh it manually — see [`u` / `update`](#manual-chaining-update--u-update).

## Great events — `sge`, `ege`, `cge`

A great event is a long-running activity (e.g. a trip, a workday) that can absorb
later entries into its category. Active great events appear in the header.

| Command | Meaning |
|---------|---------|
| `sge <category>` | Start a great event under the given category |
| `ege [text]` | End the great event, logging an entry |
| `cge` | Cancel the great event without logging |

While a great event is active, the journal category picker offers a
`0 = Great Event only` option so an entry can be attributed solely to the event.

If you cancel the time confirmation when ending with `ege` (or `ee` for a running
event), the entry is not logged and the event is **kept active** so nothing is
lost — the app tells you it's still running and how to end (`ege`/`ee`) or cancel
(`cge`/`ce`) it.

## Manual chaining update — `u` (alias `update`)

Refresh the `last_action` timestamp to now. Handy when you did something but
didn't log it, so a following `ln` measures from the right point.

| Command | Meaning |
|---------|---------|
| `u` | Set `last_action` to now |
| `update` | Same, alias |

## Multi-line input

For entries that span several lines, and for `ln`/`ee`/`ege`:

1. Type `:m` and press Enter.
2. Enter each line; they are collected.
3. Finish with three dashes alone on a line: `---`.

The collected text becomes a single entry (or a single chained/ended event).
