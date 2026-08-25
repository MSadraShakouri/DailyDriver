# DailyDriver v2.1.0

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
- **Unified day timeline** — `day` interleaves journal, prayers, sleep, naps,
  qada, and targets chronologically, with a midnight / day-start boundary
  toggle.
- **Search** over journal text and categories, grouped by how many words match.
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

See **[Getting Started](https://msadrashakouri.ir/DailyDriver/getting-started/)**
for the `da` alias and the Termux quick-entry dialog.

---

## Documentation

The live docs are built with **[Astro Starlight](https://starlight.astro.build/)**
and published to GitHub Pages:

- **[DailyDriver Docs](https://msadrashakouri.ir/DailyDriver/)** — the site
- Getting started — `docs/getting-started.md`
- Command reference — `docs/commands/`
- Concepts — `docs/concepts/`
- Architecture · Roadmap — `docs/architecture.md`, `docs/roadmap.md`

Docs source lives in **[`docs/`](docs/)** (plain markdown, GitHub-readable).
The site config lives in **[`docs-site/`](docs-site/)** and builds from `docs/`
via a temp sync workflow — no duplicate markdown is committed.
Published by **[docs workflow](.github/workflows/docs.yml)**.

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
