# DailyDriver shell completion (zsh) for the `da` alias / main.py CLI.
#
# Install — source this file from ~/.zshrc:
#   source /path/to/DailyDriver/completions/daily.zsh
#
# It locates main.py relative to this file. Override with:
#   export DAILYDRIVER_MAIN=/path/to/DailyDriver/main.py

: "${_dailydriver_main:=${DAILYDRIVER_MAIN:-$(cd "${(%):-%N:h}/.." && pwd)/main.py}}"

_dailydriver_complete() {
    local cur=""
    if [ "$CURRENT" -le "${#words[@]}" ]; then
        cur="${words[CURRENT]}"
    fi
    local -a before=()
    local i
    for (( i = 2; i < CURRENT && i <= ${#words[@]}; i++ )); do
        before+=("${words[i]}")
    done
    local line
    if [ "${#before[@]}" -eq 0 ]; then
        line="$cur"
    else
        # When the cursor sits after a space, $cur is empty and the trailing
        # space is preserved — the engine needs it to tell "qada " from "qada".
        line="${before[*]} $cur"
    fi
    local -a candidates
    candidates=("${(@f)$(python3 "$_dailydriver_main" --complete "$line" 2>/dev/null)}")
    compadd -a candidates
}

compdef _dailydriver_complete da main.py
