# TODO

## High Priority
- **Show Hijri and Gregorian dates in header**  
  Display equivalent Gregorian and Hijri dates below the main Jalali header border (dimmed, one row).

## Medium Priority
- **HTML editor for categories (merging, etc.)**  
  Extend the existing keyword editor to merge, rename, or delete categories. Useful for long‑term maintenance.
- **View entry (read‑only) from view/search**  
  Typing an entry ID shows the entry details without opening the editor.  
  Add a separate `e` or `edit` key to jump into the editor from that view.
- **Quick‑add templates**  
  One‑word shortcuts that expand to a full entry with a preset category and optional duration (e.g., `bath` → logs a 10‑minute bathroom entry).
- **Enhanced statistics (word counts, chronotype, sleep consistency, prayer times, category trends, year progress)**  
  - Average words per journal entry over 7/14 days.  
  - Tiny bar chart of entries per day (7 days).  
  - Histogram of most‑logged hours (chronotype).  
  - Sleep regularity: avg sleep‑start and wake time ± variance (7/14 days).  
  - Prayer time distribution for each slot (avg, earliest, latest) over 7/14 days.  
  - Category trend arrows comparing last 7/14 days to previous period.  
  - Year progress bar (Jalali) in stats (not header).
- **Recall command**  
  Randomly display a past journal entry, automatically excluding categories like `hygiene/*`.  
  Configurable exclude list in `meta` table. Simple `r`=next, `v`=full view, `q`=quit.
- **Mood tracking (random prompts a few times a day)**  
  Lightweight mood logging with optional note. Random timer or prompt at next interaction after a cooldown.  
  *(Mood stats will be added after this base is implemented.)*
- **Quick notes (temporary entry, not saved to DB)**  
  A scratchpad that holds a draft, reviewable and optionally saveable later. Needs a small state file and commands like `sn` / `save` / `discard`.
- **In‑app viewing of past data (export‑like but interactive)**  
  Richer day view that also shows summaries, logs, and stats inline without exporting to a file.
- **“now” command**  
  Quick one‑shot status: next prayer countdown, today’s entry count, maybe active great event. Useful for `da now`.
- **Reminders overhaul (birthdays & events)**  
  Currently `remind: true` shows every day for 14 days – too noisy.  
  Birthdays: configurable importance level → shows at intervals (e.g., important: 1 month, 3 weeks, 2 weeks, 1 week, last 3 days; normal: 2 weeks, 1 week, last 3 days).  
  Calendar events: similar schedule, not daily for two weeks.
- **Random fun stats**  
  Show a fun statistic (word count record, longest entry, top category, sleep record…) a few times a day (max 3) without time pressure. Colorful, not tied to header refresh.

## Low Priority
- **Daily quote / hadith**  
  Scrape or load from an offline file a short inspirational quote or hadith. Display in header or a dedicated command.
- **Prayer times for other cities**  
  Add data for additional cities similar to Tehran’s lookup. Likely needs a settings/configuration file.
- **Weather for other cities (or other sources)**  
  Allow switching city or adding alternative weather sources (e.g., OpenWeatherMap fallback).
- **TUI (replace print/input)**  
  Major refactor to a full terminal UI library (e.g., Textual, ncurses). Defer to a later major version.
- **Generic reminders / deadlines**  
  Allow adding a remind‑me flag to any entry, not just calendar events. Builds on existing intentions and `remind` logic.  
  *Note: intentions need a complete rework first – the current table/command are unused.*
- **Log additional weather data (wind, humidity, etc.)**  
  Scrape extra fields from IRIMO and store them in the `weather_log` table.  
  Keep the header clean; data is for future reference, stats, or export.  
  No UI change except a possible `weather full` command to view details.
- **Keyword editor: show original unstemmed word**  
  Add a “search” button in the keyword editor that lazily looks up the original unstemmed text from the entry that created the keyword, without adding a new DB column.
