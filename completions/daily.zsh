# DailyDriver shell completion (zsh) for the `da` alias / main.py CLI.
#
# Install — source this file from ~/.zshrc *after* compinit runs
# (at the end of the file is safest; oh-my-zsh runs compinit itself):
#   source /path/to/DailyDriver/completions/daily.zsh
#
# Candidates come from `main.py --complete`, resolved in this order:
#   1. $DAILYDRIVER_MAIN (explicit override),
#   2. main.py next to this script's checkout (if readable),
#   3. `da` on PATH (`da --complete`).
# Debug with: echo "$_dailydriver_main"

_dailydriver_script_main() {
    # NOTE: dirname here must use %/* stripping — a :h suffix inside the
    # :- default does NOT take the dirname (it stays literal text).
    local src="${(%):-%N}"
    case "$src" in
        */*) src="${src%/*}" ;;
        *) src="$PWD" ;;
    esac
    printf '%s' "$(cd "$src/.." && pwd)/main.py"
}

# Resolved once at source time (kept in a global for debugging).
if [ -n "${DAILYDRIVER_MAIN:-}" ]; then
    _dailydriver_main="$DAILYDRIVER_MAIN"
else
    _dailydriver_main="$(_dailydriver_script_main)"
    if [ ! -r "$_dailydriver_main" ]; then
        _dailydriver_main=""
    fi
fi

_dailydriver_complete() {
    local cur="" line i
    local -a before=()
    local -a candidates=()
    if [ "$CURRENT" -le "${#words[@]}" ]; then
        cur="${words[CURRENT]}"
    fi
    for (( i = 2; i < CURRENT && i <= ${#words[@]}; i++ )); do
        before+=("${words[i]}")
    done
    if [ "${#before[@]}" -eq 0 ]; then
        line="$cur"
    else
        # When the cursor sits after a space, $cur is empty and the trailing
        # space is preserved — the engine needs it to tell "qada " from "qada".
        line="${before[*]} $cur"
    fi
    local output=""
    if [ -n "$_dailydriver_main" ]; then
        output="$(python3 "$_dailydriver_main" --complete "$line" 2>/dev/null)"
    elif command -v da >/dev/null 2>&1; then
        output="$(da --complete "$line" 2>/dev/null)"
    fi
    if [ -n "$output" ]; then
        candidates=("${(@f)output}")
        # -U: the engine already filtered (fuzzily); don't let zsh re-filter by prefix.
        # -V: keep the engine's best-first order instead of sorting alphabetically.
        compadd -U -V dailydriver -a candidates
    fi
}

if command -v compdef >/dev/null 2>&1; then
    compdef _dailydriver_complete da main.py ./main.py
else
    echo "dailydriver completion: compdef not found — source daily.zsh after compinit runs" >&2
fi
