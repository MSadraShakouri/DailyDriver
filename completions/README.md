# Shell completion for the `da` CLI

The REPL completes commands inline (via `prompt_toolkit`). These scripts bring
the same engine — subcommands, flags, target names, qada entries, categories —
to single-shot CLI calls (`da qada log <TAB>`).

All three scripts call `main.py --complete "<partial line>"`, which shares the
REPL's completion engine (`dailydriver/ui/completion.py`), so the two never
drift. Database-backed candidates (target names, categories, …) are read from
your usual database (`data/daily.db`, or `$DAILYDRIVER_DB`).

## Install

```bash
# bash — add to ~/.bashrc:
source /path/to/DailyDriver/completions/daily.bash

# zsh — add to ~/.zshrc:
source /path/to/DailyDriver/completions/daily.zsh

# fish — link once:
mkdir -p ~/.config/fish/completions
ln -s /path/to/DailyDriver/completions/daily.fish ~/.config/fish/completions/da.fish
```

The scripts find `main.py` relative to their own location. If you moved them,
point at your checkout explicitly:

```bash
export DAILYDRIVER_MAIN=/path/to/DailyDriver/main.py   # bash/zsh
set -Ux DAILYDRIVER_MAIN /path/to/DailyDriver/main.py  # fish
```

Completion is registered for the `da` alias and for `main.py`. If your alias
has a different name, add it: `complete -F _dailydriver_complete myalias`
(bash) or `compdef _dailydriver_complete myalias` (zsh).

## Notes

- Names containing spaces complete only up to the first space (shell
  word-splitting). Prefer dash/underscore names for targets and qada entries.
- Free-text commands (`v`, `ee`, journal lines, …) intentionally offer no
  candidates besides `-h` / `--help`.
