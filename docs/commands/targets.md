# Targets — `nazr`, `habit`, `targets`

Track goals with intervals, progress, and counters. There are two kinds:

- **nazr** — *finite* goals (a fixed total to reach, e.g. a vowed number of prayers or charitable acts).
- **habit** — *indefinite* goals repeated on a schedule (daily/weekly/n-day).

`nazr` and `habit` open the manager filtered to that kind; `targets` opens it with everything.

## Logging (inline)

These are routine logging actions and keep their inline syntax. `<kind>` is `nazr` or `habit`.

| Usage | Meaning |
|-------|---------|
| `<kind> log <name> <amount> [-n]` | Log progress by `amount` (`-n` / `--no-last` skips updating `last_action`) |
| `<kind> daily_total <name> <total> [-n]` | Set today's total; logs the difference already done today |
| `<kind> counter_total <name> <value> [-n]` | Log the difference from the stored counter, then store `value` |
| `<kind> counter_reset <name>` | Reset the stored counter to 0 (logs nothing) |

Examples:

```
nazr log tasbih 33
habit log reading 10 -n
habit daily_total pushups 50
habit counter_total steps 8200 --no-last
```

`daily_total` and `counter_total` refuse to log a negative difference and warn you to adjust manually instead.

## The manager (interactive)

Creating and editing targets is a deliberate action, so it lives in the manager (open with `nazr`, `habit`, or `targets`):

- `l <#> <amount>` — log progress
- `dt <#> <total>` — set today's total
- `ct <#> <value>` — update counter and log the difference
- `cr <#>` — reset counter
- `p <#>` — pause / unpause
- `e <#>` — edit entry
- `d <#>` — delete entry
- `a` — add a new entry
- `?` — help
- `q` — quit

Overdue targets appear in the header and are highlighted in the manager.
