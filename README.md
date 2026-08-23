# DailyDriver v1.7.0

Your personal, terminal‑based life tracker.  
Log prayers, sleep, hygiene routines, birthdays, intentions, and free‑form journal entries – all from a fast, keyboard‑driven REPL.  
Built with Python, SQLite, and Jalali calendar support.

---

## Features

- **Prayer tracking** – Fajr, Dhuhr/Asr, Maghrib/Isha with jamaat and shak options, dynamic Tehran times. Includes **backlog marking (`p q`)** for overdue prayers (logs at current time) and smart header nudges.
- **Qada & Fasting** – interactive backlog manager for missed prayers and fasting with progress tracking, pause/resume, and interval scheduling (`qada`).
- **Targets (Nazr & Habits)** – track finite (nazr) and indefinite (habit) goals with daily/weekly/n‑day intervals, counter support, and interactive manager (`nazr`, `habit`, `targets`).
- **Sleep & nap logging** – bed/wake times, auto‑calculated duration; track short naps separately.
- **Weather** – Tehran weather scraped from IRIMO, displayed in the header with emoji (cached hourly).
- **Day navigation** – browse any day with `day YYYY-MM-DD` or `-1`, and jump multiple days (e.g. `5n`, `5p`).
- **Hygiene reminders** – define intervals for habits, get nudges when overdue. Respects day‑start hour (default 4:00 AM) for before‑dawn logs.
- **Birthday list** – Jalali dates, upcoming birthday alerts with age, reminder levels.
- **Intentions** – to‑dos with deadlines and expected durations.
- **Journal entries** – free‑text with smart time parsing (e.g. `13:00`, `2‑3`, `yesterday`).
- **Great events & chaining** – start a long activity, later end and log it.
- **Smart categories** – TF‑IDF keyword learning from your entries (exact path‑match boost).
- **Statistics** – prayer adherence, sleep averages, hygiene conformance, top categories.
- **Three‑calendar events** – Jalali, Gregorian, and Hijri events with per‑calendar icons (🔆🌐🌙) and holiday confetti (🎊). Reminders with configurable schedules and a visual reminder editor.
- **Global Hijri date offset** – interactive `hijri` command to apply a correction for moon‑sighting differences. Stored in a version‑controlled file.
- **Full‑text search** (`search` command) with fuzzy time/date/category boosting, and multi‑page navigation (`5n`).
- **Reminders** – mark events with reminder levels (0‑1‑2) and see them in the header ahead of time. Birthdays and calendar events follow separate schedules based on importance.
- **Beautiful header** – today’s prayers, sleep, weather, birthdays, hygiene, events, reminders, tomorrow preview, and prayer nudges at a glance. Color‑coded overdue/pre‑alert, reverse‑video today in calendars.
- **Unified time expressions** – a single flexible syntax for all time input: single times, ranges, offsets, durations, `l`/`last` and `n`/`now` atoms. Works across journal, sleep, nap, and prayer.
- **Header redesign** – modern centered date block with Jalali weekday, thin separator, Gregorian/Hijri dates, improved spacing.
- **`recent` command** – layout matches `view` and `search` with wrapped categories and descriptions.
- **State files moved into the database** – no more hidden dot‑files.
- **Built‑in aliases** – `pray` → `p`, `sleep` → `s`, `h` → `?`, `qada` → now a full feature (not an alias).
- **Travel mode** – disable location‑dependent features (weather, prayer nudges) with a smart slot selector for prayer.
- **Day start hour** – shift the day boundary (default 4:00 AM) for hygiene and target calculations (`daystart`).
- **Void scratchpad** – unfiltered thoughts, separate from the main journal (`v`, `void`, `vexport`).
- **Manual chaining update** – `u` / `update` refreshes `last_action` for chaining.
- **Termux‑dialog integration** – `-md` / `--termux-dialog` flag opens an Android text dialog for quick journal entries.
- **Test isolation** – database path configurable via `DAILYDRIVER_DB` env var; tests pass on clean clone. **303 tests** total.
- **Minimal dependencies** – Python 3.10+, SQLite, `jdatetime`, `hijridate`, `porter2stemmer`.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/MSadraShakouri/DailyDriver.git
   cd DailyDriver
   ```

2. Install the project and all dependencies:
   ```bash
   pip install .
   ```

   This automatically installs `jdatetime`, `hijridate`, and `porter2stemmer`.

3. (Optional) Make the entry point executable:
   ```bash
   chmod +x main.py
   ```

4. Create a convenient command (optional):
   - Symlink:
     ```bash
     ln -s /full/path/to/DailyDriver/main.py ~/.local/bin/daily
     ```
   - Alias (add to `~/.bashrc` or `~/.zshrc`):
     ```bash
     alias daily='python /path/to/DailyDriver/main.py'
     ```

---

## Quick Start

Launch the app:

```bash
./main.py
# or if you set up the symlink:
daily
```

You’ll see the daily header and a prompt `>`. Type `?` for a command overview, or just start writing a journal entry.

```
> today was a productive day
```

---

## Basic Commands

| Command | Description |
|---------|-------------|
| `p` | Log a prayer |
| `p q` | Mark a past unlogged prayer as qada (logs at current time) |
| `s` | Log sleep |
| `nap` | Log a short nap |
| `day` / `today` | View today or any past/future day (with navigation) |
| `recent` | Show last 5 journal entries |
| `view` | Browse journal entries |
| `search` | Full‑text search with fuzzy boosts |
| `stats` | Statistics (30 days) |
| `cal` | Clean month calendar (today highlighted) |
| `year` | Responsive year calendar |
| `export` | Export sleep/prayers/entries to Markdown (use `--txt` for plain text) |
| `hijri` | Show/adjust Hijri date offset (interactive) |
| `qada` | Interactive backlog manager for prayers and fasting |
| `nazr` / `habit` / `targets` | Track finite and indefinite goals |
| `travel` | Toggle travel mode (disables location‑dependent features) |
| `daystart` | Show/set day boundary hour (default 4:00 AM) |
| `v` / `void` | Scratchpad entry (no time parsing, no keywords) |
| `u` / `update` | Manually refresh `last_action` for chaining |
| `?` | Full help and keyword list |
| `q` | Quit |

**Aliases:** `pray` → `p`, `sleep` → `s`, `h` → `?`.

For the complete command reference, see **[COMMANDS.md](COMMANDS.md)**.

---

## Data Storage & Privacy

All your data is stored in **`data/daily.db`** (SQLite). No network calls, no third‑party analytics.
To inspect the database directly:

```bash
sqlite3 data/daily.db ".tables"
sqlite3 data/daily.db "SELECT * FROM entries;"
```

---

## Project Structure (abbreviated)

```
dailydriver/
├── core/          # database, migration, logger, keyword learner
├── features/      # prayer, sleep, hygiene, birthdays, calendar, events, weather, intentions, qada, targets, void
├── display/       # header renderer, display utilities, stats
├── cli/           # REPL, dispatcher, commands, search, calendar views, export
├── ui/            # terminal abstraction
└── utils/         # time helpers, unified time parser, intervals, prayer_times
data/              # database, stopwords, event JSON files, hijri offset
tools/             # event editor, keyword editor, reminder editor
tests/             # test files (header, commands, logger state, etc.)
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'jdatetime'`**
→ `pip install jdatetime`

**`ModuleNotFoundError: No module named 'hijridate'`**
→ `pip install hijridate`

**`ModuleNotFoundError: No module named 'porter2stemmer'`**
→ `pip install porter2stemmer`

**Header looks misaligned or truncated**
→ Resize your terminal to at least 80 columns.

**Database empty after moving the folder**
→ Run `main.py` from the `DailyDriver/` directory.

**Tests fail with "no such table" after clone**
→ Run `python tests/run_all.py` – it creates a temporary database automatically. You can also set the environment variable `DAILYDRIVER_DB` to point to a writable path for `pytest`‑based runs.

---

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for guidelines.

---

## License

MIT License. See `LICENSE` file for details.

---

Made with ❤️ for a mindful, organised life.  
May your prayers be on time and your sleep restful.
