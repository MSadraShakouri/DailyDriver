# DailyDriver shell completion (fish) for the `da` alias / main.py CLI.
#
# Install:
#   mkdir -p ~/.config/fish/completions
#   ln -s /path/to/DailyDriver/completions/daily.fish ~/.config/fish/completions/da.fish
#
# It locates main.py relative to this file. Override with:
#   set -Ux DAILYDRIVER_MAIN /path/to/DailyDriver/main.py

function __dailydriver_main
    if test -n "$DAILYDRIVER_MAIN"
        echo "$DAILYDRIVER_MAIN"
    else
        echo (dirname (status --current-filename))/../main.py
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
    python3 (__dailydriver_main) --complete "$line" 2>/dev/null
end

complete -c da -f -a '(__dailydriver_candidates)'
complete -c main.py -f -a '(__dailydriver_candidates)'
