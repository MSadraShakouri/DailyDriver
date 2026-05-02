# DailyDriver v2.1.0

Your personal, terminal‑based life tracker.
Log prayers, sleep, hygiene routines, birthdays, intentions, and free‑form journal entries – all from a fast, keyboard‑driven REPL.
Built with Python, SQLite, and Jalali calendar support.

---

## Features

- **Prayer tracking** – Fajr, Dhuhr/Asr, Maghrib/Isha with jamaat and shak options, dynamic Tehran times.
- **Sleep logging** – bed/wake times, auto‑calculated duration.
- **Hygiene reminders** – define intervals for habits, get nudges when overdue.
- **Birthday list** – Jalali dates, upcoming birthday alerts with age.
- **Intentions** – to‑dos with deadlines and expected durations.
- **Journal entries** – free‑text with smart time parsing (e.g. `13:00`, `2‑3`, `yesterday`).
- **Great events & chaining** – start a long activity, later end and log it.
- **Smart categories** – automatic keyword learning from your entries.
- **Statistics** – prayer adherence, sleep averages, hygiene conformance, top categories.
- **Three‑calendar events** – Jalali, Gregorian, and Hijri events displayed dynamically.
- **Reminders** – mark events with `remind: true` and see them in the header two weeks ahead.
- **Beautiful header** – today’s prayers, sleep, birthdays, hygiene, events, and reminders at a glance.
- **Minimal dependencies** – Python 3.8+, SQLite, `jdatetime`, `hijridate`.

---

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/MSadraShakouri/DailyDriver.git
   cd DailyDriver
   ```

2. Install the required packages:
   ```bash
   pip install jdatetime hijridate
   ```

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
| `s` | Log sleep |
| `view` | Browse journal entries |
| `today` | Today’s summary |
| `stats` | Statistics (30 days) |
| `cal` | Clean month calendar |
| `year` | Responsive year calendar |
| `export` | Export sleep/prayers/entries to a file |
| `?` | Full help and keyword list |
| `q` | Quit |

For a complete command reference, see **[COMMANDS.md](COMMANDS.md)**.

---

## Data Storage & Privacy

All your data is stored in **`data/daily.db`** (SQLite). No network calls, no third‑party analytics.
To inspect the database directly:

```bash
sqlite3 data/daily.db ".tables"
sqlite3 data/daily.db "SELECT * FROM entries;"
```

---

## Project Structure

```
dailydriver/
├── core/          # database, parser, logger, keyword learning
├── domains/       # prayer, sleep, hygiene, birthday, intention, prayer times
├── display/       # header, stats, today view, hygiene nudges
├── cli/           # REPL, commands, calendar, export
├── ui/            # terminal abstraction
└── utils/         # time helpers, calendar events
data/              # database, stopwords, event JSON files
tools/             # event editor (mobile‑friendly web UI)
tests/             # test files
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'jdatetime'`**
→ `pip install jdatetime`

**`ModuleNotFoundError: No module named 'hijridate'`**
→ `pip install hijridate`

**Header looks misaligned or truncated**
→ Resize your terminal to at least 80 columns.

**Database empty after moving the folder**
→ Run `main.py` from the `DailyDriver/` directory.

---

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for guidelines.

---

## License

MIT License. See `LICENSE` file for details.

---

Made with ❤️ for a mindful, organised life.
May your prayers be on time and your sleep restful.
