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
| `p q` | Mark a past unlogged prayer as qada (logs at the current time) |
| `p q -15` | Mark past with 15 min ago |
| `p q 03:11` | Mark past at 03:11 on that day |

Prayer times are dynamically interpolated for Tehran based on monthly data
(configurable in `dailydriver/features/prayer/_prayer_times.py`).

---

### Sleep Logging `s` (and `sleep` alias)

| Usage | Description |
|-------|-------------|
| `s 23:00 07:15` | Sleep at 23:00, wake at 07:15 |
| `s 23-7:15` | Shorthand form (sleep‑wake) |
| `s n 08:00` | `n` = now (sleep time is right now) |
| `s -30 08:00` | Fell asleep 30 minutes ago |
| `s l-9` | From last action to 09:00 |
| `s 23-n` | From 23:00 to now |
| `s ln` | From last action to now |
| `s l--10` | From last action to 10 minutes ago |

---

### Time Expressions

The app uses a unified time‑expression language that works everywhere
(journal, sleep, nap, prayer).  
A time expression can be a single point or a range.

**Single times**

| Example | Meaning |
|---------|---------|
| `09:18` | 09:18 today (or yesterday if already passed) |
| `-15` | 15 minutes ago |
| `l` / `last` | Last action time |
| `n` / `now` | Current time |

**Ranges**

| Example | Meaning |
|---------|---------|
| `9:18-9:24` | From 09:18 to 09:24 |
| `-15-n` | From 15 minutes ago until now |
| `l-18:30` | From last action to 18:30 |
| `l--15m` | From last action to 15 minutes ago |
| `l+5m` | From last action + 5 minutes (forward) |
| `19:00--15m` | From 19:00 to 15 minutes ago |
| `23-n` | From 23:00 to now |
| `ln` | From last action to now |
| `last5m` / `l5m` | Last 5 minutes (range from now‑5m to now) |

Durations can be written as `30m`, `1h`, `1h15m`, or a bare number for minutes.

---

### Free‑Text Journal Entry

Anything not recognised as a command is treated as a journal entry.
The app will:
1. Parse any time expressions (using the language above) and ask for confirmation.
2. Suggest categories based on learned keywords.
3. Ask for a category if none matched.

If a great event is active and suggestions are shown, the category picker also
offers `0 = Great Event only`.

Examples:
```
> read Quran for 30 minutes
> worked on project from 9‑12
> last Thursday visited grandmother
```

---

### Day View `day`, `today`

| Usage | Description |
|-------|-------------|
| `day` | Show today’s view |
| `day -1` | Yesterday |
| `day 1405-02-15` | Specific Jalali date |

Navigation inside the view: `(p)rev`, `(n)ext`, `YYYY-MM-DD` to jump, `5n`/`5p` to move multiple days, `q` to quit.
From `view` or `search`, use `d <id>` to open the day of that entry.

---

### Viewing Entries `view`

| Usage | Description |
|-------|-------------|
| `view` | Show all entries, newest first |
| `view project` | Filter by category containing “project” |

Navigation: `n` next, `p` previous, `q` quit, multi‑page jump with `5n`. Type an entry ID to edit it, or `d <id>` to open that entry’s day.

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

### Targets `nazr`, `habit`, `targets`

Track finite (nazr) and indefinite (habit) goals with intervals and progress tracking.

| Usage | Description |
|-------|-------------|
| `nazr` | Open manager (filtered to nazr entries) |
| `habit` | Open manager (filtered to habit entries) |
| `targets` | Open manager (all entries) |
| `nazr log <name> <amount>` | Log progress for a nazr entry |
| `habit log <name> <amount>` | Log progress for a habit entry |
| `nazr daily_total <name> <total>` | Set today's total (logs the difference) |
| `habit daily_total <name> <total>` | Set today's total (logs the difference) |
| `nazr counter_total <name> <value>` | Log the difference from the last counter value |
| `habit counter_total <name> <value>` | Log the difference from the last counter value |
| `nazr counter_reset <name>` | Reset the counter to 0 (no log) |
| `habit counter_reset <name>` | Reset the counter to 0 (no log) |

Inside the manager:
- `l <#> <amount>` – log progress
- `dt <#> <total>` – set today's total
- `ct <#> <value>` – update counter and log difference
- `cr <#>` – reset counter
- `p <#>` – pause/unpause
- `e <#>` – edit entry
- `d <#>` – delete entry
- `a` – add new entry
- `?` – help
- `q` – quit

---

### Qada `qada`

Interactive manager for tracking missed prayers and fasting obligations.

| Usage | Description |
|-------|-------------|
| `qada` | Open the interactive manager (fixed 4 entries: Fajr, Dhuhr/Asr, Maghrib/Isha, Fasting) |
| `qada log <slot\|id> [amount]` | Log progress for a prayer entry (e.g., `qada log fajr 4`) |
| `qada fasting yes` | Log today's fast |
| `qada fasting no` | Pause fasting for 1 day |

Inside the manager:
- `l <#>` – log progress for entry #
- `p <#>` – pause/unpause entry #
- `e <#>` – edit entry (target/interval)
- `?` – help
- `q` – quit

---

### Travel Mode `travel`

Disables location‑dependent features (weather, prayer nudges). Prayer in travel mode shows a smart slot selector.

| Usage | Description |
|-------|-------------|
| `travel` | Toggle travel mode |
| `travel on` | Enable travel mode |
| `travel off` | Disable travel mode |
| `travel status` | Show current state |

---

### Day Start Hour `daystart`

Shift the day boundary for hygiene and target calculations. Default is 4:00 AM.

| Usage | Description |
|-------|-------------|
| `daystart` | Show current day start hour |
| `daystart <0-23>` | Set day start hour |

---

### Void `v`, `void`, `vexport`

Unfiltered thoughts, completely separate from the main journal. No time parsing, no categories, no keywords, and does not update `last_action`.

| Usage | Description |
|-------|-------------|
| `v <text>` | Log a void entry |
| `void <text>` | Log a void entry (alias) |
| `vexport <duration\|all>` | Export void entries to Markdown (e.g., `vexport 7d`, `vexport all`) |

---

### Update `u`, `update`

Manually refresh the `last_action` timestamp for chaining (`ln`). Useful when you've done something but didn't log it.

| Usage | Description |
|-------|-------------|
| `u` | Update `last_action` to now |
| `update` | Update `last_action` to now (alias) |

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
| `cal` | Current month grid (today highlighted) |
| `cal 6` | Month 6 (Shahrivar) of current year |
| `cal 6 1405` | Month 6 of year 1405 |

The grid follows the Unix `cal` style with Saturday–Friday week.

---

### Year Calendar `year`

Displays the full Jalali year in a responsive multi‑column grid.
Today’s date is displayed in reverse video in each month grid.
Column count adapts to terminal width (1, 2, or 3 per row).
Official holidays are listed below the grid.

---

### Export `export`

| Usage | Description |
|-------|-------------|
| `export 7d` | Export last 7 days as a Markdown timeline |
| `export 2w --txt` | Export last 2 weeks as a plain-text timeline |
| `export 3m` | Export last 3 months |
| `export 1y` | Export last 1 year |
| `export all` | Export everything with no cutoff |

The export is a single chronological timeline grouped by day. Journal entries,
sleep, naps, prayers, qada progress, and target logs are interleaved naturally.
Markdown keeps the familiar journal-style bullets, times, and quoted details;
`--txt` produces the same timeline in plain text.

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

Results are paginated; press `n`/`p` to navigate (multi‑page with `5n`), `q` to quit, enter an entry ID to edit it, or `d <id>` to open that entry’s day view.
Matching search terms are highlighted in reverse video.

---

### Nap `nap`

| Usage | Description |
|-------|-------------|
| `nap 14:00 14:25` | Nap from 14:00 to 14:25 |
| `nap 14-14:25` | Compact form (like sleep) |
| `nap l-14:00` | From last action to 14:00 |
| `nap l--5` | From last action to 5 minutes ago |

Naps are shown in the daily header (total nap time) and `today` summary.
Typing `nap` alone prints usage and exits.

---

### Recent Entries `recent`

Shows the last 5 journal entries in a modern, wrapped layout identical to `view`.

---

### Hijri Offset `hijri`

Always interactive. Opens a menu to choose an offset (-2 to +2) for Hijri date conversion.

| Usage | Description |
|-------|-------------|
| `hijri` | Show current Hijri date with offsets and select one |

---

### Multi‑Line Input

1. Type `:m` and press Enter.
2. Each subsequent line is collected.
3. Finish with three dashes on a line by itself: `---`.
4. The whole text becomes a single entry.

This also works with `ln`, `ee`, and `ege` commands for chaining or ending events.

---

### Help `?`

Displays all commands and learned category keywords.

---

### Quit `q`

Exits the app. All data is saved instantly.
