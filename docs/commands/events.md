# Events & Chaining

DailyDriver supports numbered category states, single running timers, and chaining from the last action.

## Numbered category states — `st1`–`st9`, `et...`

A numbered state is a timed, category-injecting context. Slots 1–9 can run independently; each can hold several categories. Every journal entry logged while states are active receives the union of their categories. Active states appear in the header.

| Command | Meaning |
|---------|---------|
| `st1 <category...>` | Start state 1 with one or more categories |
| `st1 <category...> -u` | Also set `last_action` to the state start time |
| `et1 [text]` | End state 1; with text, log its timed entry |
| `et31 [text]` | End states 3 and 1 together |
| `ln4 <text>` | Chain from `last_action` to now, then end state 4 |

Examples:

```text
> st1 transport/car
> st2 friends/a
> et1 reached the metro
> st3 transport/metro friends/b
> et31 arrived together
```

State categories are created when the state starts. State starts do not update `last_action` by default; `-u` (or `--update-last`, anywhere after the command) opts in. The state’s own start time is always recorded.

For an `et` command with text, **the first state number is the time anchor** for its single journal entry. For example, `et21 arrived` uses state 2’s start time, logs one entry with categories that are active at that moment, and then ends states 2 and 1. If the time confirmation is cancelled, all selected states remain active. Without text, `et` only stops the selected states: it creates no entry and does not update `last_action`.

Each active state also gets **its own header line** — `⏱ 3 friends/b food/lunch · 15:30` — so a long category name wraps instead of pushing later slots off a narrow screen.

When injected categories are active, the category picker lists them as **Already injected** and omits them from both the numbered suggestions and the Prompt Toolkit dropdown. When additional suggestions are available, `0` means “already injected only” (no additional categories).

## Running event — `se`, `ee`, `ce`

Legacy single running timer, retained with its existing behavior.

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

Log an entry spanning from your **last action** until now, without having started a timer. Useful when you finish something and want to log it after the fact.

| Command | Meaning |
|---------|---------|
| `ln [text]` | Log from `last_action` to now |
| `ln4 <text>` | Log from `last_action` to now, then end state 4 |
| `ln1352 <text>` | Same, ending states 1, 3, 5 and 2 |

```
> ln replied to emails
> st4 friends/b
  ... (chat; log other things meanwhile, each picking up friends/b) ...
> ln4 said goodbye
```

The numbered form keeps **`ln` timing**: the entry spans `last_action` → now, *not* the state's own start — that is what `et4 <text>` does. It is the fast way to close a state whose categories were being injected into everything you logged while it ran. Text is required, so a bare `ln4` changes nothing, and the listed states stay active if you cancel the time confirmation. Only slots 1–9 exist; `ln0` and `ln10` print usage rather than silently dropping the digits.

The `last_action` timestamp is updated whenever you log something. You can also refresh it manually — see [`u` / `update`](#manual-chaining-update--u-alias-update).

## Great events — `sge`, `ege`, `cge`

Legacy single great event, retained with its existing behavior. A great event is a long-running activity whose categories are injected into later entries.

| Command | Meaning |
|---------|---------|
| `sge <category...>` | Start a great event with one or more categories |
| `ege [text]` | End the great event, logging an entry |
| `cge` | Cancel the great event without logging |

Great-event categories are created when `sge` starts. While active, the picker identifies them as already injected.

If you cancel the time confirmation when ending with `ege` (or `ee` for a running event), the entry is not logged and the event is **kept active** so nothing is lost — the app tells you it's still running and how to end (`ege`/`ee`) or cancel (`cge`/`ce`) it.

## Manual chaining update — `u` (alias `update`)

Refresh the `last_action` timestamp to now. Handy when you did something but didn't log it, so a following `ln` measures from the right point.

| Command | Meaning |
|---------|---------|
| `u` | Set `last_action` to now |
| `update` | Same, alias |

## Multi-line input

For entries that span several lines, and for `ln`/`ln...`/`ee`/`ege`/`et...`:

1. Type `:m` and press Enter.
2. Enter each line; they are collected.
3. Finish with three dashes alone on a line: `---`.

The collected text becomes a single entry (or a single chained/ended event).
