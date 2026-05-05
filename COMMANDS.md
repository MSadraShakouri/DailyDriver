# Command Reference

Commands are case‑insensitive and usually a single letter or word.
Arguments are separated by spaces.

---

### Prayer Logging `p`

| Usage | Description |
|-------|-------------|
| `p` | Log current slot (auto‑guessed) |
| `p -15` | 15 minutes before the fixed prayer time |
| `p 05:30` | Explicitly at 05:30 (slot guessed from hour) |
| `p j` | With jamaat (no location) |
| `p j masjid` | With jamaat at a given location |
| `p s 3` | With shak count of 3 |

Prayer times are dynamically interpolated for Tehran based on monthly data
(configurable in `dailydriver/domains/prayer_times.py`).

---

### Qada / Missed Prayers `rq`, `mp`

- `rq` – List unlogged slots (newest first) and mark one as **qada**.
- `mp` – Same listing, but you can mark as **missed** or **qada**.

---

### Sleep Logging `s`

| Usage | Description |
|-------|-------------|
| `s 23:00 07:15` | Sleep at 23:00, wake at 07:15 |
| `s 23-7:15` | Shorthand form (sleep‑wake) |
| `s n 08:00` | `n` = now (sleep time is right now) |
| `s -30 08:00` | Fell asleep 30 minutes ago |

---

### Free‑Text Journal Entry

Anything not recognised as a command is treated as a journal entry.
The app will:
1. Parse any time expressions (e.g. `13:00`, `2‑3`, `yesterday`) and ask for confirmation.
2. Suggest categories based on learned keywords.
3. Ask for a category if none matched.

Examples:
```
> read Quran for 30 minutes
> worked on project from 9‑12
> last Thursday visited grandmother
```

---

### Viewing Entries `view`

| Usage | Description |
|-------|-------------|
| `view` | Show all entries, newest first |
| `view project` | Filter by category containing “project” |

Navigation: `n` next, `p` previous, `q` quit. Type an entry ID to edit it.

---

### Birthdays `bd`

| Usage | Description |
|-------|-------------|
| `bd` | Interactive prompts |
| `bd Ali 1386/05/12` | Full date |
| `bd Zahra 5/12` | Month/day only |

---

### Hygiene Tracking `hygiene`

Opens an interactive manager: `a` add, `e` edit, `d` delete, `q` quit.
Example items: `shaving`, `brushing_teeth`, `laundry`.
Log an entry under a category like `hygiene/shaving` to record the last time.

---

### Intentions `t`

| Usage | Description |
|-------|-------------|
| `t` | Interactive mode |
| `t finish report` | Adds intention with description only |

Interactive mode allows setting a Jalali deadline (`YYYY/MM/DD`) and expected duration.

---

### Statistics `stats`

Shows:
- Prayer on‑time, qada, missed counts and percentages (last 30 days)
- Sleep average, best, worst (last 14 days)
- Hygiene adherence (logs vs expected)
- Top categories (last 30 days)

---

### Today’s Summary `today`

Displays today’s prayer status, sleep, and all journal entries.

---

### Great Events `sge`, `ege`, `cge`

- `sge work` – Start a great event with category “work”
- `ege finished the report` – End, log entry, and clear the great event
- `cge` – Cancel without logging

Active great events appear in the header.

---

### Chaining `ln`

- `ln replied to emails` – Log from the last action time until now.

---

### Running Event `se`, `ee`, `ce`

Fine‑grained event timing:

- `se` – Save the current time as start of an event.
- `ee something` – End the event and log the description.
- `ce` – Cancel the saved start.

---

### Calendar `cal`

| Usage | Description |
|-------|-------------|
| `cal` | Current month grid |
| `cal 6` | Month 6 (Shahrivar) of current year |
| `cal 6 1405` | Month 6 of year 1405 |

The grid follows the Unix `cal` style with Saturday–Friday week.

---

### Year Calendar `year`

Displays the full Jalali year in a responsive multi‑column grid.
Column count adapts to terminal width (1, 2, or 3 per row).
Official holidays are listed below the grid.

---

### Export `export`

| Usage | Description |
|-------|-------------|
| `export 7d` | Export last 7 days |
| `export 2w` | Export last 2 weeks |
| `export 3m` | Export last 3 months |
| `export 1y` | Export last 1 year |

Creates a human‑readable text file with sections for Sleep, Prayers, and Journal Entries.

---

### Search `search`

| Usage | Description |
|-------|-------------|
| `search programming` | Find entries containing “programming” (description or category) |
| `search morning` | Entries with start time in the morning (02‑12) – fuzzy time boost |
| `search yesterday` | Entries from the last 3 days – relative date boost |
| `search monday` | Entries from the most recent Monday ±1 day |
| `search programming night` | Scored combination: text match + time/category boosts |

Search uses SQLite FTS5 for instant text indexing, with a LIKE fallback for substring matches.
Fuzzy scoring automatically boosts results matching time‑of‑day, relative dates, weekdays,
month names (Jalali, Gregorian, Hijri), and category paths.  
Misspellings are tolerated (e.g. `mornig` → morning).

Results are paginated; press `n`/`p` to navigate, `q` to quit, or enter an entry ID to edit it.

---

### Nap `nap`

| Usage | Description |
|-------|-------------|
| `nap` | Interactive: enter start time and duration |
| `nap 30m` | Nap of 30 minutes, starting 30 minutes ago |
| `nap 14:00 14:25` | Nap from 14:00 to 14:25 |
| `nap 14:00 30m` | Nap starting at 14:00, duration 30 minutes |

Naps are shown in the daily header (total nap time) and `today` summary.

---

### Multi‑Line Input

1. Type `:m` and press Enter.
2. Each subsequent line is collected.
3. Finish with three dashes on a line by itself: `---`.
4. The whole text becomes a single entry.

---

### Help `?`

Displays all commands and learned category keywords.

---

### Quit `q`

Exits the app. All data is saved instantly.
