---
title: "DailyDriver Documentation"
---

DailyDriver is a personal, terminal-based life tracker: prayers, sleep, hygiene,
journal, targets, calendars, and search — all from a fast,
keyboard-driven prompt, with Jalali (Persian) calendar support.

This folder is the single source of truth for DailyDriver's documentation, published with Astro Starlight.

## Start here

- **[Getting Started](getting-started.md)** — install, run, the `da` alias, and
  the Termux quick-entry dialog.

## Commands

Every command, grouped by area. In the app, add `-h` or `--help` after any
command (e.g. `p -h`) for the same details, or type `?` for a summary.

- [Logging](commands/logging.md) — journal, sleep, naps, void
- [Prayer](commands/prayer.md) — `p`, qada backlog
- [Qada & Fasting](commands/qada.md)
- [Events & Chaining](commands/events.md) — `se`/`ee`/`ce`, `ln`, great events, `u`
- [Targets](commands/targets.md) — nazr and habits
- [Viewing & Summaries](commands/viewing.md) — `day`, `view`, `search`, `recent`, `stats`
- [Calendar](commands/calendar.md) — `cal`, `year`, `hijri`
- [Tools & Setup](commands/tools.md) — birthdays, intentions, hygiene, travel, day start
- [Export](commands/export.md)

## Concepts

The cross-cutting systems that aren't a single command:

- [Time Expressions](concepts/time-expressions.md) — the one syntax used everywhere
- [Categories & Keyword Learning](concepts/categories.md) — how suggestions are ranked
- [The Header](concepts/header.md) — what the daily dashboard shows
- [Calendars](concepts/calendars.md) — the three-calendar model and Hijri offset
- [Day Start Hour](concepts/day-start.md) — shifting the day boundary

## For contributors

- [Architecture](architecture.md) — layout, the feature-package contract, data model, migrations
- [Roadmap](roadmap.md) — shipped history and planned ideas
- [Reference: Optimizations](reference/optimizations.md) — performance/cleanup ideas

Repository top level keeps a short [README](https://github.com/MSadraShakouri/DailyDriver/blob/main/README.md),
[CONTRIBUTING](https://github.com/MSadraShakouri/DailyDriver/blob/main/CONTRIBUTING.md),
[CHANGELOG](https://github.com/MSadraShakouri/DailyDriver/blob/main/CHANGELOG.md), and `LICENSE`.
