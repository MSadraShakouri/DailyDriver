# TODO

## High Priority
- **HTML editor for categories (merging, etc.)**  
  Extend the existing keyword editor to merge, rename, or delete categories. Useful for long‑term maintenance.

## Medium Priority
- **Mood tracking (random prompts a few times a day)**  
  Lightweight mood logging with optional note. Random timer or prompt at next interaction after a cooldown.
- **Quick notes (temporary entry, not saved to DB)**  
  A scratchpad that holds a draft, reviewable and optionally saveable later. Needs a small state file and commands like `sn` / `save` / `discard`.
- **More built‑in aliases (no user‑defined aliases)**  
  Add aliases like `pray` → `p`, `sleep` → `s`, etc. Trivial dispatch map extension.
- **In‑app viewing of past data (export‑like but interactive)**  
  Richer day view that also shows summaries, logs, and stats inline without exporting to a file.

## Low Priority
- **Prayer times for other cities**  
  Add data for additional cities similar to Tehran’s lookup. Likely needs a settings/configuration file.
- **Weather for other cities (or other sources)**  
  Allow switching city or adding alternative weather sources (e.g., OpenWeatherMap fallback).
- **TUI (replace print/input)**  
  Major refactor to a full terminal UI library (e.g., Textual, ncurses). Defer to a later major version.
- **Generic reminders / deadlines**  
  Allow adding a remind‑me flag to any entry, not just calendar events. Builds on existing intentions and `remind` logic.


log other weather stuff but not display, its priceless
fix prayers, remove rq and mp or whatever it was, replace with a q tag which searches all the db, maybe with an index, automatically gets missed ones, option to log something late as not qada, but default to qada since ive been actually using the app
so usage would be something like `da p q` which searches for all prayers that havent been marked as read
