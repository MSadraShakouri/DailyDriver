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

The scripts find `main.py` in this order:

1. `$DAILYDRIVER_MAIN` if you export it (explicit override);
2. `main.py` next to the checkout the script was sourced from (if readable);
3. `da` on your `PATH` (runs `da --complete`).

```bash
export DAILYDRIVER_MAIN=/path/to/DailyDriver/main.py   # bash/zsh
set -Ux DAILYDRIVER_MAIN /path/to/DailyDriver/main.py  # fish
```

Notes:

- zsh: source `daily.zsh` **after** `compinit` runs (end of `~/.zshrc` is
  safest — oh-my-zsh runs `compinit` itself). Sourcing earlier prints a
  warning and registers nothing.
- fish: the symlinked install cannot resolve relatively, so fish relies on
  the override or `da` on `PATH` — set one of them.

Completion is registered for the `da` alias and for `main.py`. If your alias
has a different name, add it: `complete -F _dailydriver_complete myalias`
(bash) or `compdef _dailydriver_complete myalias` (zsh).

## Notes

- Values are matched the way fzf matches them and ordered best-first by the
  engine (`alex` or `rss` find `relatives/sam_sutherland`; `^`, `'`, `$` and `!`
  operators work inside a word). The zsh script adds the matches unfiltered
  (`compadd -U`) so zsh does not drop non-prefix hits and keeps the engine's order.
- With the [fzf-tab](https://github.com/Aloxaf/fzf-tab) zsh plugin, the engine
  hands fzf every candidate real fzf would accept (the engine's matcher is a port
  of fzf's), so `da st1 rss<TAB>` and `da st1 <TAB>` then `rss` agree.

- Names containing spaces complete only up to the first space (shell
  word-splitting). Prefer dash/underscore names for targets and qada entries.
- Free-text commands (`v`, `ee`, journal lines, …) intentionally offer no
  candidates besides `-h` / `--help`.

## Debugging

Tab does nothing? Check the pieces in order:

```bash
echo "$_dailydriver_main"              # bash/zsh: which main.py the script uses
python3 main.py --complete "travel "  # hook itself: must print on/off/status/…
```

If the hook works but Tab doesn't, the script either resolved the wrong path
(fix with `$DAILYDRIVER_MAIN`, then re-source) or never registered (zsh:
source after `compinit`; check for the warning).
