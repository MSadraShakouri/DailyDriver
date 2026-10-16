"""Context-aware tab completion for the REPL (and shell ``--complete`` hooks).

The REPL used to complete only the first word (command names). This module
completes the *whole* line: subcommands, flags, and database-backed values
(category paths, target names, qada entries, active state slots) based on the
token position.

Matching is case-insensitive substring, mirroring the category picker's
``_RankedCompleter`` so ``code`` finds ``work/code``. An empty word matches
everything, so Tab on ``travel `` lists ``on/off/status`` plus the flags.

Dynamic providers are defensive: any database error yields no candidates
rather than breaking the prompt, and results are cached briefly (keyed by
database path so tests with isolated databases never see stale entries).
"""

from __future__ import annotations

import re
import time

from prompt_toolkit.completion import Completer, Completion

# ── Static candidate tables ──────────────────────────────────────────────

TARGET_SUBCOMMANDS = ("log", "daily_total", "counter_total", "counter_reset")
TARGET_FLAGS = ("-n", "--no-last")
QADA_SUBCOMMANDS = ("log", "fasting")
QADA_SLOTS = ("fajr", "dhuhr_asr", "maghrib_isha")
QADA_FASTING_ANSWERS = ("yes", "no")
TRAVEL_ARGS = ("on", "off", "status")
DAYSTART_HOURS = tuple(str(hour) for hour in range(24))
EXPORT_DURATIONS = ("all", "7d", "14d", "30d", "2w", "3m", "1y")
EXPORT_FORMATS = ("--txt", "--md")
DAY_OFFSETS = tuple(f"-{offset}" for offset in range(1, 8))
PRAYER_FLAGS = ("j", "s", "q")
TIME_KEYWORDS = ("n", "now", "l", "last", "ln")
STATE_FLAGS = ("-u", "--update-last")
HELP_FLAGS = ("-h", "--help")
JALALI_MONTHS = (
    "Farvardin",
    "Ordibehesht",
    "Khordad",
    "Tir",
    "Mordad",
    "Shahrivar",
    "Mehr",
    "Aban",
    "Azar",
    "Dey",
    "Bahman",
    "Esfand",
)
CAL_MONTHS = tuple(str(month) for month in range(1, 13)) + JALALI_MONTHS

# REPL-only tokens that are not dispatcher commands but deserve completion.
REPL_EXTRA_COMMANDS = (":m", "---")

# Aliases resolve to their canonical command for argument specs.
_COMMAND_ALIASES = {
    "pray": "p",
    "sleep": "s",
    "void": "v",
    "update": "u",
}

# Extra dash-flags per canonical command (beyond the universal -h/--help).
_COMMAND_DASH_FLAGS: dict[str, tuple[str, ...]] = {
    "st": STATE_FLAGS,
    "nazr": TARGET_FLAGS,
    "habit": TARGET_FLAGS,
    "targets": TARGET_FLAGS,
    "export": EXPORT_FORMATS,
}

_NUMBERED_COMMAND_RE = re.compile(r"^(st|et|ln)(\d+)$", re.IGNORECASE)

# ── Dynamic providers (cached, failure-safe) ─────────────────────────────

_CACHE: dict[tuple[str, str], tuple[float, list]] = {}
# Short TTL: collapses the burst of queries from rapid keystrokes while
# staying fresh enough that a just-started state appears almost immediately.
_CACHE_TTL_SECONDS = 2.0


def clear_completion_cache() -> None:
    """Drop all cached dynamic candidates (used by tests)."""
    _CACHE.clear()


def _cached(key: str, loader):
    """Return cached ``loader()`` output, keyed by database path + ``key``."""
    try:
        from dailydriver.core.database import get_db_path

        db_path = get_db_path()
    except Exception:
        db_path = ""
    cache_key = (db_path, key)
    now = time.monotonic()
    hit = _CACHE.get(cache_key)
    if hit is not None and now - hit[0] < _CACHE_TTL_SECONDS:
        return hit[1]
    try:
        value = list(loader())
    except Exception:
        value = []
    _CACHE[cache_key] = (now, value)
    return value


def category_paths() -> list[str]:
    """All known category paths, alphabetically (for sge/st/view)."""

    def load():
        from dailydriver.core.database import get_connection_cm

        with get_connection_cm(auto=False) as conn:
            return [row["path"] for row in conn.execute("SELECT path FROM categories ORDER BY path")]

    return _cached("categories", load)


def search_vocabulary() -> list[str]:
    """Distinct words from category paths (search matches whole words)."""
    words: set[str] = set()
    for path in category_paths():
        for raw in re.split(r"[^a-zA-Z]+", path.lower()):
            if len(raw) >= 3:
                words.add(raw)
    return sorted(words)


def target_names(kind: str | None = None) -> list[str]:
    """Target entry names, optionally filtered by kind (nazr/habit)."""

    def load():
        from dailydriver.features.targets.entries import get_all_entries

        return [entry["name"] for entry in get_all_entries(kind=kind)]

    return _cached(f"targets:{kind or 'all'}", load)


def qada_names() -> list[str]:
    """Qada entry names plus ids (``qada log`` accepts slot, name, or id)."""

    def load():
        from dailydriver.features.qada.entries import list_entries

        candidates: list[str] = []
        for entry in list_entries():
            candidates.append(str(entry["name"]))
            candidates.append(str(entry["id"]))
        return candidates

    return _cached("qada", load)


def active_state_ids() -> list[int]:
    """Ids of currently active numbered states (for et/ln digit runs)."""

    def load():
        from dailydriver.core.state import get_active_numbered_states

        return [state["id"] for state in get_active_numbered_states()]

    return _cached("active_states", load)


def jalali_years() -> list[str]:
    """Current Jalali year ± 1 (for ``cal <month> <year>``)."""
    try:
        import jdatetime

        year = jdatetime.date.today().year
    except Exception:
        return []
    return [str(year - 1), str(year), str(year + 1)]


# ── Line splitting & matching ────────────────────────────────────────────


def split_completion_line(text: str) -> tuple[list[str], str]:
    """Split prompt text into (committed tokens, word being typed).

    ``"qada l"`` → ``(["qada"], "l")``; ``"qada "`` → ``(["qada"], "")``;
    ``"qa"`` → ``([], "qa")``.
    """
    if text.strip() == "":
        return [], ""
    parts = text.split()
    if text[-1].isspace():
        return parts, ""
    return parts[:-1], parts[-1]


def _match(candidates: list[str], word: str) -> list[str]:
    """Case-insensitive substring filter, order-preserving, deduplicated."""
    lowered = word.lower()
    seen: set[str] = set()
    matched: list[str] = []
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        if lowered in candidate.lower():
            matched.append(candidate)
    return matched


def _base_command(first: str, command_names: set[str] | list[str]) -> str | None:
    """Resolve the first token to a canonical command, or None if unknown.

    Compact numbered spellings (``st4``, ``et31``, ``ln1352``) resolve to
    their base command. Unknown words are journal text — no completion.
    """
    lowered = first.lower()
    numbered = _NUMBERED_COMMAND_RE.fullmatch(lowered)
    if numbered is not None:
        base = numbered.group(1)
        return base if base in command_names else None
    if lowered not in command_names:
        return None
    return _COMMAND_ALIASES.get(lowered, lowered)


# ── First-token (command) candidates ─────────────────────────────────────


def _numbered_extensions(word: str) -> list[str]:
    """One-digit extensions for a partial ``et``/``ln`` digit run.

    Only digits of *active* states are offered, excluding digits already in
    the run: with states 1, 3, 4 active, ``et3`` suggests ``et31``/``et34``.
    Runs are capped at 4 digits to bound the noise.
    """
    match = re.fullmatch(r"(et|ln)([1-9]+)", word.lower())
    if match is None or len(match.group(2)) >= 4:
        return []
    prefix, digits = match.group(1), match.group(2)
    used = set(digits)
    return [f"{prefix}{digits}{state_id}" for state_id in active_state_ids() if str(state_id) not in used]


def _first_token_candidates(word: str, command_names: list[str]) -> list[str]:
    return list(command_names) + list(REPL_EXTRA_COMMANDS) + _numbered_extensions(word)


# ── Per-command argument candidates ──────────────────────────────────────


def _duration_already_present(args: list[str]) -> bool:
    from dailydriver.core.export_utils import parse_duration_arg

    return any(parse_duration_arg(arg) is not None for arg in args)


def _arg_candidates(base: str, args: list[str]) -> list[str]:
    """Positional candidates for *base* given the committed *args*."""
    lowered_args = [arg.lower() for arg in args]

    if base == "travel":
        return list(TRAVEL_ARGS) if not args else []

    if base == "daystart":
        return list(DAYSTART_HOURS) if not args else []

    if base == "export":
        candidates: list[str] = []
        if not _duration_already_present(args):
            candidates.extend(EXPORT_DURATIONS)
        if not any(arg in EXPORT_FORMATS for arg in lowered_args):
            candidates.extend(EXPORT_FORMATS)
        return candidates

    if base == "vexport":
        return list(EXPORT_DURATIONS) if not _duration_already_present(args) else []

    if base == "qada":
        if not args:
            return list(QADA_SUBCOMMANDS)
        if lowered_args[0] == "log" and len(args) == 1:
            return list(QADA_SLOTS) + qada_names()
        if lowered_args[0] == "fasting" and len(args) == 1:
            return list(QADA_FASTING_ANSWERS)
        return []

    if base in ("nazr", "habit", "targets"):
        if not args:
            return list(TARGET_SUBCOMMANDS)
        if lowered_args[0] in TARGET_SUBCOMMANDS and len(args) == 1:
            kind = base if base in ("nazr", "habit") else None
            return target_names(kind)
        if lowered_args[0] in TARGET_SUBCOMMANDS and len(args) >= 2:
            return [flag for flag in TARGET_FLAGS if flag not in lowered_args]
        return []

    if base == "cal":
        if not args:
            return list(CAL_MONTHS)
        if len(args) == 1:
            return jalali_years()
        return []

    if base == "day":
        return list(DAY_OFFSETS) if not args else []

    if base == "p":
        return [flag for flag in PRAYER_FLAGS if flag not in lowered_args]

    if base in ("s", "nap"):
        return [keyword for keyword in TIME_KEYWORDS if keyword not in lowered_args]

    if base == "view":
        # ``view`` takes a single filter string: complete its first word only.
        return category_paths() if not args else []

    if base == "search":
        # Every query term can come from the vocabulary; skip typed terms.
        typed = set(lowered_args)
        return [word for word in search_vocabulary() if word not in typed]

    if base in ("sge", "st"):
        typed = set(lowered_args)
        return [path for path in category_paths() if path.lower() not in typed]

    # Free-text commands (ee/ege/et/ln/v/t/...) and bare managers take no
    # completable positionals; universal flags are appended by suggest().
    return []


def suggest(tokens: list[str], word: str, command_names: list[str] | set[str]) -> list[str]:
    """Return completion candidates for a split line (see split_completion_line)."""
    names = list(command_names)
    if not tokens:
        return _match(_first_token_candidates(word, names), word)
    base = _base_command(tokens[0], set(names))
    if base is None:
        return []
    candidates = _arg_candidates(base, tokens[1:])
    for flag in _COMMAND_DASH_FLAGS.get(base, ()):
        if flag not in candidates:
            candidates.append(flag)
    for flag in HELP_FLAGS:
        if flag not in candidates:
            candidates.append(flag)
    return _match(candidates, word)


def suggest_for_text(text: str, command_names: list[str] | set[str]) -> list[str]:
    """Convenience wrapper: split *text* (cursor at end) and suggest."""
    tokens, word = split_completion_line(text)
    return suggest(tokens, word, command_names)


# ── prompt_toolkit integration ───────────────────────────────────────────


class ReplCompleter(Completer):
    """Whole-line completer for the REPL prompt."""

    def __init__(self, command_names: list[str] | set[str]):
        self.command_names = sorted(set(command_names))

    def get_completions(self, document, complete_event):
        tokens, word = split_completion_line(document.text_before_cursor)
        for candidate in suggest(tokens, word, self.command_names):
            yield Completion(candidate, start_position=-len(word))
