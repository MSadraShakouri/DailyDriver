# DailyDriver shell completion (bash) for the `da` alias / main.py CLI.
#
# Install — source this file from ~/.bashrc:
#   source /path/to/DailyDriver/completions/daily.bash
#
# It locates main.py relative to this file. Override with:
#   export DAILYDRIVER_MAIN=/path/to/DailyDriver/main.py

if [ -z "${DAILYDRIVER_MAIN:-}" ]; then
    _dailydriver_main="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/main.py"
else
    _dailydriver_main="$DAILYDRIVER_MAIN"
fi

_dailydriver_complete() {
    local cur="${COMP_WORDS[COMP_CWORD]}"
    local line
    if [ "$COMP_CWORD" -le 1 ]; then
        line="$cur"
    else
        # Args before the current word, then the current word itself. When the
        # cursor sits after a space, $cur is empty and the trailing space is
        # preserved — the engine needs it to tell "qada " from "qada".
        line="${COMP_WORDS[*]:1:$((COMP_CWORD - 1))} $cur"
    fi
    mapfile -t COMPREPLY < <(python3 "$_dailydriver_main" --complete "$line" 2>/dev/null)
}

complete -F _dailydriver_complete da main.py ./main.py
