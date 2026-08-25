---
title: "Qada & Fasting — `qada`"
---

An interactive manager for a standing backlog of missed prayers and fasting
obligations, with progress tracking, pause/resume, and interval scheduling.

There are four fixed entries: **Fajr**, **Dhuhr/Asr**, **Maghrib/Isha**, and
**Fasting**. Overdue entries are shown persistently in the header nudges;
today's scheduled instances appear only in the final hour before the prayer.

## Commands

| Usage | Meaning |
|-------|---------|
| `qada` | Open the interactive manager |
| `qada log <slot\|id> [amount]` | Log prayer qada progress (e.g. `qada log fajr 4`) |
| `qada fasting yes` | Log today's fast |
| `qada fasting no` | Pause fasting for one day |

`qada log` and `qada fasting` are logging shortcuts, so they keep their inline
syntax. Creating, editing targets, and changing intervals happen inside the
interactive manager.

## Inside the manager

- `l <#>` — log progress for entry number `#`
- `p <#>` — pause / unpause entry `#`
- `e <#>` — edit the entry (target amount / interval)
- `?` — help
- `q` — quit

## Relationship to `p q`

`p q` (see [Prayer](prayer.md#backlog--qada-marking--p-q)) is a one-off marker
for a single missed prayer at a chosen time. The `qada` manager is for tracking
the ongoing backlog and fasting over days and weeks.
