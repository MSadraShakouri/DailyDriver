---
title: "Time Expressions"
---

DailyDriver uses one unified time-expression language everywhere time is
entered — journal entries, sleep, naps, and prayer. Learn it once and it works
across the app. A time expression is either a single point in time or a range.

## Single times

| Example | Meaning |
|---------|---------|
| `09:18` | 09:18 today (or yesterday if that time already passed) |
| `-15` | 15 minutes ago |
| `l` / `last` | The last action time |
| `n` / `now` | The current time |

AM/PM is disambiguated automatically, with 24-hour detection.

## Ranges

| Example | Meaning |
|---------|---------|
| `9:18-9:24` | From 09:18 to 09:24 |
| `-15-n` | From 15 minutes ago until now |
| `l-18:30` | From last action to 18:30 |
| `l--15m` | From last action to 15 minutes ago |
| `l+5m` | From last action forward 5 minutes |
| `19:00--15m` | From 19:00 to 15 minutes ago |
| `23-n` | From 23:00 to now |
| `ln` | From last action to now |
| `last5m` / `l5m` | The last 5 minutes (now-5m to now) |

## Durations

Durations may be written as `30m`, `1h`, `1h15m`, or a bare number for minutes.

## Where it's used

- **Journal:** any time expression in your entry text is detected and confirmed.
- **Sleep / nap:** e.g. `s 23-7:15`, `s ln`, `nap l--5`.
- **Prayer:** offsets and explicit times, e.g. `p -15`, `p 05:30`, `p q 03:11`.

When several interpretations are possible, the app lists them and lets you pick
(or type a new expression). When a time is chosen explicitly from that list, it
is not asked to be confirmed again.
