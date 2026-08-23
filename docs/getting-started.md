# Getting Started

## Requirements

- Python 3.10+
- SQLite (bundled with Python)
- Dependencies (installed automatically): `jdatetime`, `hijridate`,
  `porter2stemmer`, `prompt_toolkit`

## Install

```bash
git clone https://github.com/MSadraShakouri/DailyDriver.git
cd DailyDriver
pip install .
```

To work on the code and run the tests, install the test extra in editable mode:

```bash
pip install -e '.[test]'
python -m pytest
```

## Run

From the repository directory:

```bash
./main.py        # or: python main.py
```

You'll see the daily header followed by a `>` prompt. Type `?` for a command
summary, add `-h` after any command for its details, or just start writing a
journal entry:

```
> today was a productive day
```

Press `q` to quit. All data is saved instantly to `data/daily.db`.

## The `da` alias (recommended)

Most day-to-day use is single-shot: run one command and exit immediately.
Set up a shell alias so logging is a single keystroke away.

Add to `~/.bashrc` or `~/.zshrc`:

```bash
alias da='python /path/to/DailyDriver/main.py'
```

Then log without entering the interactive prompt:

```bash
da p                 # log the current prayer
da s 23:00 07:15     # log sleep
da "worked on the report 9-11"   # a journal entry
```

Anything you pass as arguments is run as one command, then the app exits. This
is the fastest workflow for muscle-memory logging.

> The rich interactive prompt (history + autocompletion) only activates in the
> full REPL on an interactive terminal. Single-shot `da` calls and piped input
> fall back to plain prompts automatically, so nothing slows down or breaks.

## Termux quick-entry dialog (Android)

On Termux you can pop a native Android text dialog for a fast journal entry:

```bash
da -md          # or: da --termux-dialog
```

This opens `termux-dialog`, takes your typed text, and logs it as a journal
entry (running category selection afterwards in the terminal). Outside Termux it
prints a short notice and exits.

## How input works

DailyDriver upgrades **input** with `prompt_toolkit` (command autocompletion,
persistent history, and an autocompleting category picker) when it runs in an
interactive terminal. When that isn't possible — piped input, redirects, a dumb
terminal, or if `prompt_toolkit` is unavailable — it silently falls back to
plain prompts and behaves exactly as before. Output (headers, tables, calendars)
is always plain text.

## Data & privacy

Everything lives in `data/daily.db` (SQLite). There are no analytics; the only
network calls are optional weather lookups (Tehran, IRIMO). Inspect the database
directly if you like:

```bash
sqlite3 data/daily.db ".tables"
sqlite3 data/daily.db "SELECT * FROM entries LIMIT 5;"
```

You can point the app or the tests at a different database with the
`DAILYDRIVER_DB` environment variable.
