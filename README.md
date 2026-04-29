# DailyDriver v2.0.0

Your personal, terminal‑based life tracker.  
Log prayers, sleep, hygiene routines, birthdays, intentions, and free‑form journal entries – all from a fast, keyboard‑driven REPL.  
Built with Python, SQLite, and Jalali calendar support.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [The REPL Interface](#the-repl-interface)
- [Command Reference](#command-reference)
  - [Prayer Logging `p`](#prayer-logging-p)
  - [Qada / Missed Prayers `rq`, `mp`](#qada--missed-prayers-rq-mp)
  - [Sleep Logging `s`](#sleep-logging-s)
  - [Free‑Text Journal Entry](#free-text-journal-entry)
  - [Viewing Entries `view`](#viewing-entries-view)
  - [Birthdays `bd`](#birthdays-bd)
  - [Hygiene Tracking `hygiene`](#hygiene-tracking-hygiene)
  - [Intentions `t`](#intentions-t)
  - [Statistics `stats`](#statistics-stats)
  - [Today’s Summary `today`](#todays-summary-today)
  - [Great Events `sge`, `ege`, `cge`](#great-events-sge-ege-cge)
  - [Chaining `ln`](#chaining-ln)
  - [Running Event `se`, `ee`, `ce`](#running-event-se-ee-ce)
  - [Help `?`](#help-)
  - [Quit `q`](#quit-q)
- [Multi‑Line Input](#multi-line-input)
- [Categories & Keywords](#categories--keywords)
- [Data Storage & Privacy](#data-storage--privacy)
- [Project Structure](#project-structure)
- [Customisation](#customisation)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Prayer tracking** – Log Fajr, Dhuhr/Asr, Maghrib/Isha with exact times, optional jamaat location and shak count.
- **Sleep logging** – Record bed/wake times, auto‑calculate duration.
- **Hygiene reminders** – Define intervals for habits and get gentle nudges when overdue.
- **Birthday list** – Never miss a birthday (Jalali dates with age calculation).
- **Intentions** – Quick to‑dos with deadlines and expected durations.
- **Journal entries** – Free‑text with smart time parsing (e.g. `13:00`, `2‑3`, `yesterday`).
- **Great events & chaining** – Start a long activity, later end and log it with minimal typing.
- **Smart categories** – Automatic keyword learning from your entries.
- **Statistics** – Prayer adherence, sleep averages, hygiene conformance, top categories.
- **Jalali calendar** – Native Persian calendar; dates shown in the header and summaries.
- **Beautiful header** – Today’s prayers, sleep, upcoming birthdays, and hygiene nudges at a glance.
- **Minimal dependencies** – Python 3.8+, SQLite, `jdatetime`.

---

## Installation

1. **Clone the repository** (or place the `DailyDriver/` folder anywhere):
   ```bash
   git clone https://github.com/yourname/DailyDriver.git
   cd DailyDriver
   ```

2. **Install the required package**:
   ```bash
   pip install jdatetime
   ```

3. Make the entry point executable (optional):
   ```bash
   chmod +x main.py
   ```

4. Create a convenient command (choose one):
   - **Symlink** (recommended):
     ```bash
     ln -s /full/path/to/DailyDriver/main.py ~/.local/bin/daily
     ```
   - **Alias** (add to `~/.bashrc` or `~/.zshrc`):
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

The app will suggest categories (or let you create new ones), parse any time expressions, and save everything to `data/daily.db`.

---

## The REPL Interface

Every time you press Enter, the screen clears and the header refreshes.
The header displays:

- **Date** in Jalali format (e.g. *25 Farvardin 1405*)
- **Prayer status** for today (emoji and time, or `—` if not logged yet)
- **Sleep** duration from last night’s log
- **Upcoming birthdays** (next 7 days)
- **Hygiene nudges** when a habit is due soon or overdue
- **Active great event** indicator (if any)
- **Running event** timer (if any)
- **Last action time** in the bottom bar

---

## Command Reference

Commands are case‑insensitive, usually a single letter or short word. Arguments are separated by spaces.

### Prayer logging `p`

Log today’s prayer with optional arguments.

| Command | Description |
|---------|-------------|
| `p` | Log the prayer for the current time slot (auto‑guessed) |
| `p -15` | 15 minutes before the fixed prayer time |
| `p 05:30` | Explicitly at 05:30 (slot guessed from hour) |
| `p j` | With jamaat (no specific location) |
| `p j masjid` | With jamaat at a given location |
| `p s 3` | With shak count of 3 |

Fixed prayer times (configurable in `dailydriver/domains/prayer_core.py`):
- Fajr: 04:30
- Dhuhr & Asr: 13:00
- Maghrib & Isha: 19:30

### Qada / Missed Prayers `rq`, `mp`

- `rq` – List unlogged slots (newest first) and mark one as **qada**.
- `mp` – Same listing, but you can mark as **missed** or **qada**.

Unlogged slots are shown from the first prayer log until today.

### Sleep logging `s`

| Command | Description |
|---------|-------------|
| `s 23:00 07:15` | Sleep at 23:00, wake at 07:15 |
| `s 23-7:15` | Shorthand form (sleep – wake) |
| `s n 08:00` | `n` = now (sleep time is right now) |
| `s -30 08:00` | Offset: fell asleep 30 minutes ago |

Duration is calculated automatically.

### Free‑Text Journal Entry

Anything that isn’t a recognised command is treated as a journal entry. The app will:

1. Parse any time expressions (e.g. `13:00`, `2‑3`, `yesterday`) and ask for confirmation.
2. Suggest categories based on learned keywords.
3. Ask for a category if none matched.

Examples:
```
> read Quran for 30 minutes
> worked on project from 9‑12
> last Thursday visited grandmother
```

### Viewing Entries `view`

| Command | Description |
|---------|-------------|
| `view` | Show all entries, newest first |
| `view project` | Filter by category containing “project” |

Navigation inside the viewer: `n` next page, `p` previous, `q` quit.  
Type an entry ID (number) to edit it in your default editor (`nano` by default).

Editing an entry deletes the old record and re‑logs the text, allowing you to change categories.

### Birthdays `bd`

Add a birthday (Jalali dates).

| Command | Description |
|---------|-------------|
| `bd` | Interactive prompts |
| `bd Ali 1386/05/12` | Full date |
| `bd Zahra 5/12` | Month/day only (year unknown) |

Upcoming birthdays appear in the header for the next 7 days, with age if the year was given.

### Hygiene Tracking `hygiene`

Define personal care habits and their desired intervals. The header nudges you when something is due.

Inside the manager: `a` add, `e` edit, `d` delete, `q` quit.  
Example items: `shaving`, `brushing_teeth`, `laundry`.

Log an entry under a category like `hygiene/shaving` to record the last time.

### Intentions `t`

| Command | Description |
|---------|-------------|
| `t` | Interactive mode |
| `t finish report` | Adds intention with description only |

Interactive mode lets you set a Jalali deadline (`YYYY/MM/DD`) and expected duration (minutes).

### Statistics `stats`

Shows:
- Prayer on‑time, qada, missed counts and percentages (last 30 days)
- Sleep average, best, worst (last 14 days)
- Hygiene adherence (logs vs expected)
- Top categories (last 30 days)

### Today’s Summary `today`

A detailed view of today:
- Prayer status (emoji indicators)
- Sleep record
- All entries with time, categories, and descriptions

### Great Events `sge`, `ege`, `cge`

Start a great event, later end it and log the time automatically.

- `sge work` – Start a great event with category “work”
- `ege finished the report` – End, log entry, and clear the great event
- `cge` – Cancel without logging

Great events appear in the header while active.

### Chaining `ln`

Log an entry that started at the time of the last recorded action.

`ln replied to emails` – starts from the previous log’s end time until now.

### Running Event `se`, `ee`, `ce`

Fine‑grained event timing:

- `se` – Save the current time as the start of an event
- `ee something` – End the event and log the description
- `ce` – Cancel the saved start

The header shows a running event indicator.

### Help `?`

Displays all commands and a list of categories with their top keywords.

### Quit `q`

Exits the app. All data is saved instantly.

---

## Multi‑Line Input

1. Type `:m` and press Enter.
2. Each subsequent line is collected.
3. Finish with three dashes on a line by itself: `---`.
4. The whole text becomes a single entry.

---

## Categories & Keywords

The app automatically learns keywords from your entries.  
When you log free text and assign a category, non‑stop‑words are linked to that category.  
Future entries with similar words will suggest those categories.

Stop words are loaded from `data/stopwords.txt` (editable).

---

## Data Storage & Privacy

All your data lives in **`data/daily.db`** (SQLite).  
No network calls, no third‑party analytics. Easy to backup – just copy the file.

To inspect the database directly:
```bash
sqlite3 data/daily.db ".tables"
sqlite3 data/daily.db "SELECT * FROM entries;"
```

---

## Project Structure

```
DailyDriver/
├── main.py                    # entry point
├── README.md
├── dailydriver/
│   ├── core/
│   │   ├── database.py
│   │   ├── schema.py
│   │   ├── parser.py
│   │   ├── date_parser.py
│   │   ├── logger.py
│   │   ├── keyword_learner.py
│   │   └── entry_writer.py
│   ├── domains/
│   │   ├── prayer_core.py
│   │   ├── prayer_log.py
│   │   ├── prayer_backlog.py
│   │   ├── sleep.py
│   │   ├── hygiene.py
│   │   ├── birthday.py
│   │   └── intention.py
│   ├── display/
│   │   ├── header.py
│   │   ├── display_utils.py
│   │   ├── stats.py
│   │   ├── today.py
│   │   └── hygiene_nudges.py
│   ├── cli/
│   │   ├── commander.py
│   │   ├── entry_viewer.py
│   │   └── help.py
│   ├── ui/
│   │   └── terminal_ui.py
│   └── utils/
│       └── time_utils.py
├── data/
│   ├── daily.db
│   └── stopwords.txt
└── tests/
    └── .gitkeep
```

---

## Customisation

- **Prayer times** – edit `PRAYER_TIMES` in `dailydriver/domains/prayer_core.py`.
- **Hygiene early warning thresholds** – tweak the thresholds in `dailydriver/display/hygiene_nudges.py`.
- **Text editor** – change `nano` to your preferred editor in `dailydriver/cli/entry_viewer.py` (function `edit_entry`).
- **Date format** – adjust the `strftime` formats in `dailydriver/utils/time_utils.py`.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'jdatetime'`**  
→ `pip install jdatetime`

**Header looks misaligned or truncated**  
→ Resize your terminal to at least 80 columns.

**Database is empty after moving the folder**  
→ Ensure you run `main.py` from the `DailyDriver/` directory, or update `DB_NAME` in `dailydriver/core/database.py`.

**Multi‑line input doesn’t end**  
→ Type exactly `---` on an empty line (no extra spaces).

---

## Contributing

Pull requests are welcome. Please respect the package layout:
- `core/` – data, parsing, logging
- `domains/` – one domain per file (prayer, sleep, etc.)
- `display/` – header building and display utilities
- `cli/` – REPL logic, commands
- `ui/` – terminal abstraction
- `utils/` – shared helpers

For major changes, please open an issue first to discuss your ideas.

---

## License

MIT License. See `LICENSE` file for details.

---

Made with ❤️ for a mindful, organised life.  
May your prayers be on time and your sleep restful.
