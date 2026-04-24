DailyDriver v1.0

Your personal, terminal‑based life tracker.
Log prayers, sleep, hygiene routines, birthdays, intentions, and free‑form journal entries – all from a fast, keyboard‑driven REPL.
Built with Python, SQLite, and Jalali calendar support.

---

Table of Contents

· Features
· Installation
· Quick Start
· The REPL Interface
· Command Reference
  · Prayer Logging (P)
  · Qada / Missed Prayers (RQ, MP)
  · Sleep Logging (S)
  · Free‑Text Journal Entry
  · Viewing Entries (view)
  · Birthdays (BD)
  · Hygiene Tracking (hygiene)
  · Intentions (T)
  · Statistics (stats)
  · Today’s Summary (today)
  · Flags Manager (flags)
  · Help (?)
  · Quit (q)
· Multi‑Line Input
· Categories & Keywords
· Flags
· Data Storage & Privacy
· Customisation
· Troubleshooting
· Contributing
· License

---

Features

· Prayer tracking – log Fajr, Dhuhr/Asr, Maghrib/Isha with exact times.
· Sleep logging – record bed/wake times, auto‑calculate duration.
· Hygiene reminders – define intervals for habits (shaving, teeth, etc.) and get nudges when overdue.
· Birthday list – never miss a birthday (Jalali dates supported, with age calculation).
· Intentions – set tasks with optional deadlines and expected durations.
· Journal entries – quickly capture thoughts, automatically categorised by keywords.
· Smart parsing – natural time expressions like 13:00, 2‑3, yesterday, last Monday are understood.
· Flags – tag entries with custom tokens (late, urgent, etc.) for filtering.
· Statistics – see prayer adherence, sleep averages, hygiene conformance, and top categories.
· Jalali calendar – all dates are in the Jalali (Persian) calendar; Gregorian conversions happen transparently.
· Beautiful header – a glance shows today’s prayers, sleep, upcoming birthdays, and hygiene nudges.
· Minimal dependencies – Python 3.8+, SQLite, and the jdatetime library.

---

Installation

1. Clone the repository (or place the DailyDriver/ folder anywhere you like):
   ```bash
   git clone https://github.com/yourname/DailyDriver.git
   cd DailyDriver
   ```
2. Install the single required Python package:
   ```bash
   pip install jdatetime
   ```
3. Make the main script executable (optional, for direct launch):
   ```bash
   chmod +x DailyDriver/main.py
   ```
4. Add a shebang if your main.py doesn’t already have one:
   ```python
   #!/usr/bin/env python3
   ```
   Then you can run it with ./DailyDriver/main.py.
5. Create a convenient command (choose one):
   · Symlink (recommended):
     ```bash
     ln -s /full/path/to/DailyDriver/main.py ~/.local/bin/daily
     ```
     Now typing daily launches the app from anywhere.
   · Alias (add to ~/.bashrc or ~/.zshrc):
     ```bash
     alias daily='python /path/to/DailyDriver/main.py'
     ```

---

Quick Start

Launch the app:

```bash
./DailyDriver/main.py
# or if you set up the symlink:
daily
```

You’ll see the daily header and a prompt >. Type ? for a command overview, or just start typing a journal entry.

Your first action could be:

```
> today was a good day
```

DailyDriver will ask for a category (you can create one on the fly) and optional flags.
That’s it – data is saved automatically to daily.db.

---

The REPL Interface

Every time you press Enter, the screen clears and the header refreshes.
The header shows:

· Date in Jalali format (e.g., 25 Farvardin 1405).
· Prayer status for today: a coloured emoji and the time you logged (or — if not yet logged).
· Sleep duration from last night’s log.
· Upcoming birthdays in the next 7 days.
· Hygiene nudges if a habit is due soon or overdue.

Below the header, the prompt waits for your command.

---

Command Reference

Commands are case‑insensitive and almost always a single letter or word.
Arguments are separated by spaces.

Prayer Logging (P)

Log today’s prayer with an optional time adjustment.

Command Description
P Log the prayer for the current time slot (automatically guessed).
P -15 Log the prayer, but 15 minutes before the fixed prayer time.
P 05:30 Explicitly log at 05:30 (slot is guessed from the hour).
P dhuhr_asr -5 Log a specific slot with an offset.

When you enter a time, you will be shown a confirmation before saving.

Fixed prayer times (configurable in prayer.py):

· Fajr: 04:30
· Dhuhr & Asr: 13:00
· Maghrib & Isha: 19:30

Qada / Missed Prayers (RQ, MP)

Retrospectively fill in missed prayers.

· RQ – List unlogged slots (newest first) and mark one as qada (late but performed).
· MP – Same listing, but you can mark as missed or qada.

Select a number from the list to log.
The app only shows dates from the first prayer log to today.

Sleep Logging (S)

Record when you went to bed and when you woke up.

Command Description
S 23:00 07:15 Sleep at 23:00, wake at 07:15.
S 23-7:15 Shorthand form (sleep – wake).
S 01:00 09 Integer hour for wake time (9 = 09:00).
S n 08:00 n = now (sleep time is right now).
S -30 08:00 Offset: fell asleep 30 minutes ago.

Duration is calculated automatically and saved.

Free‑Text Journal Entry

Type anything that isn’t a recognised command, and it will be logged as an entry.
DailyDriver will:

1. Parse any time expressions in your text (e.g. 13:00, 2‑3, yesterday) and ask for confirmation.
2. Suggest categories based on keywords it has learned.
3. Prompt you to attach flags.

Examples:

```
> read Quran for 30 minutes
> worked on project from 9-12
> last Thursday visited grandmother
```

Viewing Entries (view)

Browse past entries in pages of 20.

Command Description
view Show all entries, newest first.
view project Filter by category containing “project”.
During viewing: n next page, p previous, q quit. 
Enter an entry ID (number) Open that entry in an editor (nano by default).

Editing an entry deletes the old record and re‑logs the text (allowing you to change categories and flags).

Birthdays (BD)

Add a birthday (Jalali dates).

Command Description
BD Interactive prompts.
BD Ali 1386/05/12 Specify name and full date.
BD Zahra 5/12 Month/day only (year unknown).

The header will show birthdays within the next 7 days, including age if the year was provided.

Hygiene Tracking (hygiene)

Define personal care habits and their desired intervals. The header will nudge you when something is due.

Command Description
hygiene Opens the hygiene manager.
Inside the manager: a add item, e edit interval, d delete, q quit. 

Example items: shaving, brushing_teeth, laundry.
When you later log an entry under a category ending with /item (e.g., hygiene/shaving), the system records the last time.

Intentions (T)

Set a to‑do with optional deadline and expected duration.

Command Description
T Interactive mode.
T finish report Adds intention with description only.
During interactive mode you can set a Jalali deadline (YYYY/MM/DD) and expected minutes. 

Intentions are stored but not yet actively reminded – future versions will integrate them into the header.

Statistics (stats)

Shows:

· Prayer on‑time, qada, missed counts and percentages (last 30 days).
· Sleep average, best, and worst (last 14 days).
· Hygiene adherence (logs vs expected).
· Most used flags and top categories (last 30 days).

Today’s Summary (today)

A detailed view of everything logged today:

· Prayer status (with emoji indicators).
· Sleep record.
· All entries with time, categories, and flags.

Flags Manager (flags)

Define short tokens that can be attached to entries for tagging.

Command Description
flags Opens the flags manager.
Inside: a add flag (token, label, scope), e edit, d delete. 

Flags can be global or scoped to a specific category.

Help (?)

Displays all commands, a list of categories with their top keywords, and defined flags.

Quit (q)

Exits the application. All data is saved instantly – no unsaved changes.

---

Multi‑Line Input

To write a longer journal entry across several lines:

1. Type :m and press Enter.
2. You are now in multi‑line mode. Each line you type is collected.
3. When you’re done, type three dashes on a line by themselves: ---.
4. The whole text is treated as a single entry.

---

Categories & Keywords

DailyDriver automatically learns keywords from your entries.
When you log a free‑text entry and assign it a category, every non‑stop‑word in the text is linked to that category.
Later, when you type a similar entry, the app suggests the most relevant categories.

You can see the learned keywords in the ? help screen.
There’s no direct command to remove keywords yet; you can manually edit the SQLite DB if needed.

---

Flags

Flags are short strings you can attach to any entry.
Examples: late, urgent, home, work, m (for “mobile”).
Use them to mark special circumstances – they appear in the today and stats views.

Flags can be created:

· On the fly when logging an entry (just type the token at the prompt).
· From the flags manager, where you can also set a scope (the flag only appears for a certain category).

---

Data Storage & Privacy

All your data lives in a single file: daily.db (SQLite).
It is created in the same directory as main.py.

· No network calls.
· No third‑party analytics.
· You can back it up by simply copying the .db file.

To see or modify data directly, use the sqlite3 command:

```bash
sqlite3 daily.db ".tables"
sqlite3 daily.db "SELECT * FROM entries;"
```

---

Customisation

· Prayer times – edit the PRAYER_TIMES dictionary in prayer.py.
· Hygiene early warning thresholds – tweak the if desired >= … logic in header_data.py.
· Text editor – change nano to your preferred editor in view.py (function edit_entry).
· Date format – adjust the strftime in utils.py.

---

Troubleshooting

Problem: ModuleNotFoundError: No module named 'jdatetime'
Solution: Run pip install jdatetime.

Problem: The header looks misaligned or truncated.
Solution: Your terminal might be too narrow; resize it to at least 80 columns.

Problem: daily.db is empty after moving the folder.
Solution: The database is created relative to the working directory. Always run main.py from inside the DailyDriver/ folder, or update the DB_NAME path in database.py.

Problem: Multi‑line input doesn’t end.
Solution: Make sure you type exactly --- on an empty line, no extra spaces.

---

Contributing

Pull requests are welcome! Please keep the architecture clean:

· main.py – control flow only.
· header_data.py – data gathering for the display.
· display.py – terminal rendering.
· Other modules each own a single domain (prayer, sleep, etc.).

For major changes, open an issue first to discuss what you’d like to change.

---

License

MIT License. See LICENSE file for details.

---

Made with ❤️ for a mindful, organised life.
May your prayers be on time and your sleep restful.
