# DailyDriver shell completion (fish) for the `da` alias / main.py CLI.
#
# Install:
#   mkdir -p ~/.config/fish/completions
#   ln -s /path/to/DailyDriver/completions/daily.fish ~/.config/fish/completions/da.fish
#
# Candidates come from `main.py --complete`, resolved in this order:
#   1. $DAILYDRIVER_MAIN (explicit override),
#   2. main.py next to this script's checkout (if readable),
#   3. `da` on PATH (`da --complete`).
# NOTE: a symlinked install cannot resolve relatively (the link lives in
# ~/.config/fish/completions), so fish relies on 1 or 3 in practice — keep
# `da` on PATH or export DAILYDRIVER_MAIN.

function __dailydriver_main
    if test -n "$DAILYDRIVER_MAIN"
        echo "$DAILYDRIVER_MAIN"
        return
    end
    set -l rel (dirname (status --current-filename))/../main.py
    if test -r "$rel"
        echo "$rel"
    end
end

function __dailydriver_candidates
    # Full command line up to the cursor, minus the command word itself.
    # A trailing space is preserved — the engine needs it to tell
    # "qada " from "qada".
    set -l cl (commandline -c)
    set -l line (string replace -r '^[^\s]+\s*' '' -- "$cl")
    if test "$line" = "$cl"
        set line ""
    end
    set -l main (__dailydriver_main)
    if test -n "$main"
        python3 "$main" --complete "$line" 2>/dev/null
    else if command -q da
        da --complete "$line" 2>/dev/null
    end
end

complete -c da -f -a '(__dailydriver_candidates)'
complete -c main.py -f -a '(__dailydriver_candidates)'
