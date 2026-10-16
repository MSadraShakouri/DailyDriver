# DailyDriver shell completion (bash) for the `da` alias / main.py CLI.
#
# Install — source this file from ~/.bashrc:
#   source /path/to/DailyDriver/completions/daily.bash
#
# Candidates come from `main.py --complete`, resolved in this order:
#   1. $DAILYDRIVER_MAIN (explicit override),
#   2. main.py next to this script's checkout (if readable),
#   3. `da` on PATH (`da --complete`).
# Debug with: echo "$_dailydriver_main"

_dailydriver_script_main() {
    local src="${BASH_SOURCE[0]}"
    case "$src" in
        */*) : ;;
        *) src="$PWD/$src" ;;
    esac
    printf '%s' "$(cd "$(dirname "$src")/.." && pwd)/main.py"
}

_dailydriver_resolve_main() {
    if [ -n "${DAILYDRIVER_MAIN:-}" ]; then
        printf '%s' "$DAILYDRIVER_MAIN"
    else
        local script_main
        script_main="$(_dailydriver_script_main)"
        if [ -r "$script_main" ]; then
            printf '%s' "$script_main"
        fi
    fi
}

# Resolved once at source time (kept in a global for debugging).
_dailydriver_main="$(_dailydriver_resolve_main)"

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
    local output=""
    if [ -n "$_dailydriver_main" ]; then
        output="$(python3 "$_dailydriver_main" --complete "$line" 2>/dev/null)"
    elif command -v da >/dev/null 2>&1; then
        output="$(da --complete "$line" 2>/dev/null)"
    fi
    COMPREPLY=()
    if [ -n "$output" ]; then
        if [ "${BASH_VERSINFO[0]:-0}" -ge 4 ]; then
            mapfile -t COMPREPLY <<<"$output"
        else
            # Bash 3 (e.g. macOS default): no mapfile, fall back to word
            # splitting (names with spaces complete partially).
            # shellcheck disable=SC2207
            COMPREPLY=($output)
        fi
    fi
}

complete -F _dailydriver_complete da main.py ./main.py
