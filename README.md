# DailyDriver v2.0.0

Your personal, terminal-based life tracker.
Log prayers, sleep, hygiene routines, birthdays, intentions, targets, and
free-form journal entries — all from a fast, keyboard-driven prompt.
Built with Python, SQLite, and Jalali (Persian) calendar support.

---

## Highlights

- **Prayer & qada** — daily prayers with jamaat/shak options and dynamic Tehran
  times; a backlog manager for missed prayers and fasting.
- **Sleep, naps, journal** — smart, unified time parsing everywhere you type a
  time.
- **Targets** — finite goals (nazr) and repeating habits with intervals and
  counters.
- **Calendars** — Jalali, Gregorian, and Hijri at once, with events, reminders,
  and an adjustable Hijri offset.
- **Full-text search** with fuzzy time/date/category boosts.
- **Smart categories** — TF-IDF keyword learning with an autocompleting,
  ranked picker.
- **Unified export** — one chronological timeline across journal, sleep, prayer,
  qada, and targets.
- **Fast input** — command autocompletion and persistent history via
  prompt_toolkit, with automatic plain-terminal fallback.

---

## Quick start

```bash
git clone https://github.com/MSadraShakouri/DailyDriver.git
cd DailyDriver
pip install .
./main.py
```

At the `>` prompt, type `?` for a command summary, add `-h` after any command
for details (e.g. `p -h`), or just start writing a journal entry.

A shell alias makes single-shot logging instant:

```bash
alias da='python /path/to/DailyDriver/main.py'
da p                 # log the current prayer
da s 23:00 07:15     # log sleep
da "worked on the report 9-11"
```

See **[Getting Started](docs/getting-started.md)** for the `da` alias and the
Termux quick-entry dialog.

---

## Documentation

Full documentation lives in **[`docs/`](docs/README.md)**:

- [Getting Started](docs/getting-started.md)
- Command reference — [Logging](docs/commands/logging.md),
  [Prayer](docs/commands/prayer.md), [Qada](docs/commands/qada.md),
  [Events & Chaining](docs/commands/events.md),
  [Targets](docs/commands/targets.md),
  [Viewing & Summaries](docs/commands/viewing.md),
  [Calendar](docs/commands/calendar.md), [Tools & Setup](docs/commands/tools.md),
  [Export](docs/commands/export.md)
- Concepts — [Time Expressions](docs/concepts/time-expressions.md),
  [Categories](docs/concepts/categories.md), [The Header](docs/concepts/header.md),
  [Calendars](docs/concepts/calendars.md), [Day Start](docs/concepts/day-start.md)
- [Architecture](docs/architecture.md) · [Roadmap](docs/roadmap.md)

---

## Data & privacy

All data is stored locally in `data/daily.db` (SQLite). No analytics; the only
network calls are optional Tehran weather lookups. Point the app or tests at a
different database with the `DAILYDRIVER_DB` environment variable.

---

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** and the
[architecture guide](docs/architecture.md).

## License

MIT License. See the `LICENSE` file.

---

Made with care for a mindful, organised life.
May your prayers be on time and your sleep restful.
