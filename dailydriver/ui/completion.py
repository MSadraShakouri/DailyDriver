"""Context-aware tab completion engine (REPL + shell ``--complete`` hook).

The REPL used to complete only the first word (command names). This module
completes the *whole* line: subcommands, flags, and database-backed values
(category paths, target names, qada entries, active state slots) based on the
token position. The optional text on ``et...`` is the exception to free-text
completion: it can suggest only categories from currently running numbered
states, never the full category catalog.

Matching is case-insensitive substring, mirroring the category picker's
``_RankedCompleter`` so ``code`` finds ``work/code``. An empty word matches
everything, so Tab on ``travel `` lists ``on/off/status`` plus the flags.

Performance notes (every shell Tab spawns a fresh interpreter):

- This module imports **stdlib only**. The prompt_toolkit completer classes
  live in :mod:`dailydriver.ui.completion_ptk` so ``main.py --complete`` never
  pays for that import.
- Providers query SQLite directly instead of going through feature modules:
  importing any feature submodule would run the whole feature-package
  ``__init__`` chain. Most results are cached briefly (keyed by database path
  so tests with isolated databases never see stale entries); active state
  status is read fresh so numbered command availability updates immediately.
- Dynamic providers are defensive: any database error yields no candidates
  rather than breaking the prompt.

Free-text commands (journal lines, ``v``, ``ee``, …) intentionally return no
positional candidates; every known command still offers ``-h``/``--help``.
"""

from __future__ import annotations

import re
import time

# ── Static candidate tables ──────────────────────────────────────────────

TARGET_SUBCOMMANDS = ("log", "daily_total", "counter_total", "counter_reset")
TARGET_FLAGS = ("-n", "--no-last")
TARGET_KINDS = ("nazr", "habit")
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

# REPL-only tokens that are not dispatcher commands but deserve completion
# in the REPL. Excluded from shell completion (see ``include_repl_extra``).
REPL_EXTRA_COMMANDS = (":m", "---")

# Static snapshot of every first-word token (dispatcher keys plus the
# single-slot ``st1``…``ln9`` spellings) for the ``--complete`` hook, which
# must not import the dispatcher (that pulls in every feature package).
# Guarded by a parity test — update it when commands change.
STATIC_COMMAND_NAMES = (
    "?",
    "bd",
    "birthdays",
    "cal",
    "ce",
    "cge",
    "city",
    "day",
    "daystart",
    "ee",
    "ege",
    "et",
    "et1",
    "et2",
    "et3",
    "et4",
    "et5",
    "et6",
    "et7",
    "et8",
    "et9",
    "export",
    "h",
    "habit",
    "hijri",
    "hygiene",
    "ln",
    "ln1",
    "ln2",
    "ln3",
    "ln4",
    "ln5",
    "ln6",
    "ln7",
    "ln8",
    "ln9",
    "nap",
    "nazr",
    "p",
    "pray",
    "q",
    "qada",
    "recent",
    "s",
    "se",
    "search",
    "sge",
    "sleep",
    "st",
    "st1",
    "st2",
    "st3",
    "st4",
    "st5",
    "st6",
    "st7",
    "st8",
    "st9",
    "stats",
    "t",
    "targets",
    "today",
    "travel",
    "u",
    "update",
    "v",
    "vexport",
    "view",
    "void",
    "year",
)

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
_END_STATE_COMMAND_RE = re.compile(r"^et([1-9]+)$", re.IGNORECASE)
_ACTIVE_STATE_METADATA_KEY_RE = re.compile(r"^numbered_state_([1-9])_(start|categories)$")

# ── Dynamic providers (cached, failure-safe) ─────────────────────────────

_CACHE: dict[tuple[str, str], tuple[float, list]] = {}
# Short TTL: collapses bursts of catalog queries from rapid REPL keystrokes.
# Active numbered-state data is deliberately not cached, so slots can become
# unavailable/available as soon as a state starts or ends.
_CACHE_TTL_SECONDS = 2.0


def clear_completion_cache() -> None:
    """Drop all cached dynamic candidates (used by tests)."""
    _CACHE.clear()


def _cached(key: str, loader):
    """Return cached ``loader()`` output, keyed by database path + ``key``."""
    try:
        from dailydriver.core.database import get_db_path

        db_path = get_db_path()
    except Exception:  # noqa: BLE001 - completion must never break the prompt
        db_path = ""
    cache_key = (db_path, key)
    now = time.monotonic()
    hit = _CACHE.get(cache_key)
    if hit is not None and now - hit[0] < _CACHE_TTL_SECONDS:
        return hit[1]
    try:
        value = list(loader())
    except Exception:  # noqa: BLE001 - completion must never break the prompt
        value = []
    _CACHE[cache_key] = (now, value)
    return value


def _query_column(sql: str, params: tuple = ()) -> list:
    """Run a read-only query and return its rows (direct SQL, no features)."""
    from dailydriver.core.database import get_connection_cm

    with get_connection_cm(auto=False) as conn:
        return conn.execute(sql, params).fetchall()


def category_paths() -> list[str]:
    """All known category paths, alphabetically (for sge/st/view)."""

    def load():
        return [row["path"] for row in _query_column("SELECT path FROM categories ORDER BY path")]

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
        if kind is not None and kind not in TARGET_KINDS:
            return []
        if kind is None:
            rows = _query_column("SELECT name FROM target_entries ORDER BY name")
        else:
            rows = _query_column("SELECT name FROM target_entries WHERE kind = ? ORDER BY name", (kind,))
        return [row["name"] for row in rows]

    return _cached(f"targets:{kind or 'all'}", load)


def qada_names() -> list[str]:
    """Qada entry names plus ids (``qada log`` accepts slot, name, or id)."""

    def load():
        candidates: list[str] = []
        for row in _query_column("SELECT id, name FROM qada_entries ORDER BY name"):
            candidates.append(str(row["name"]))
            candidates.append(str(row["id"]))
        return candidates

    return _cached("qada", load)


def _active_numbered_state_data() -> dict[int, list[str]]:
    """Return live numbered-state categories, keyed by active slot id."""
    try:
        rows = _query_column("SELECT key, value FROM meta WHERE key GLOB 'numbered_state_[1-9]_*'")
    except Exception:  # noqa: BLE001 - completion must never break the prompt
        return {}

    stored: dict[int, dict[str, str]] = {}
    for row in rows:
        match = _ACTIVE_STATE_METADATA_KEY_RE.fullmatch(row["key"])
        if match is None:
            continue
        state_id = int(match.group(1))
        stored.setdefault(state_id, {})[match.group(2)] = str(row["value"] or "")

    active: dict[int, list[str]] = {}
    for state_id, state in stored.items():
        try:
            int(state.get("start", ""))
        except (TypeError, ValueError):
            continue
        active[state_id] = state.get("categories", "").split()
    return active


def active_state_ids() -> list[int]:
    """Ids of currently active numbered states (for et/ln digit runs)."""
    return sorted(_active_numbered_state_data())


def active_numbered_state_categories() -> list[str]:
    """Deduplicated categories injected by currently active numbered states."""
    return _dedupe_state_categories(_active_numbered_state_data())


def _end_state_categories(command: str) -> list[str]:
    """Categories from running states, but only for a valid active ``et...``."""
    match = _END_STATE_COMMAND_RE.fullmatch(command.lower())
    if match is None:
        return []

    digits = match.group(1)
    state_ids = [int(digit) for digit in digits]
    if len(set(state_ids)) != len(state_ids):
        return []

    active_states = _active_numbered_state_data()
    if not set(state_ids).issubset(active_states):
        return []
    return _dedupe_state_categories(active_states)


def _dedupe_state_categories(active_states: dict[int, list[str]]) -> list[str]:
    """Return unique paths from a live numbered-state snapshot."""
    paths: list[str] = []
    seen: set[str] = set()
    for state_id in sorted(active_states):
        for path in active_states[state_id]:
            lowered = path.lower()
            if lowered not in seen:
                paths.append(path)
                seen.add(lowered)
    return paths


def jalali_years() -> list[str]:
    """Current Jalali year ± 1 (for ``cal <month> <year>``)."""
    try:
        import jdatetime

        year = jdatetime.date.today().year
    except Exception:  # noqa: BLE001 - completion must never break the prompt
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


def _numbered_extensions(word: str, active_ids: set[int] | None = None) -> list[str]:
    """One-digit extensions for a valid active ``et``/``ln`` digit run.

    Existing digits must all refer to distinct active slots before another can
    be appended: with states 1, 3, 4 active, ``et3`` suggests ``et31``/``et34``
    but ``et5`` and ``et11`` do not grow into invalid command names. Runs are
    capped at 4 digits to bound the noise.
    """
    match = re.fullmatch(r"(et|ln)([1-9]+)", word.lower())
    if match is None or len(match.group(2)) >= 4:
        return []

    prefix, digits = match.group(1), match.group(2)
    used = {int(digit) for digit in digits}
    if len(used) != len(digits):
        return []
    if active_ids is None:
        active_ids = set(active_state_ids())
    if not used.issubset(active_ids):
        return []
    return [f"{prefix}{digits}{state_id}" for state_id in sorted(active_ids) if state_id not in used]


def _numbered_command_is_available(command: str, active_ids: set[int]) -> bool:
    """Whether a compact numbered command is meaningful in the live state."""
    match = _NUMBERED_COMMAND_RE.fullmatch(command.lower())
    if match is None:
        return True

    prefix, digits = match.groups()
    state_ids = [int(digit) for digit in digits]
    if prefix == "st":
        return len(state_ids) == 1 and state_ids[0] not in active_ids
    return len(set(state_ids)) == len(state_ids) and set(state_ids).issubset(active_ids)


def _start_command_is_available(command: str) -> bool:
    """A compact ``stN`` is available only when its slot is not running."""
    match = re.fullmatch(r"st([1-9])", command.lower())
    return match is not None and int(match.group(1)) not in set(active_state_ids())


def _first_token_candidates(word: str, command_names: list[str], include_repl_extra: bool = True) -> list[str]:
    active_ids: set[int] | None = None
    if word == "":
        # Bare Tab shows base commands only: the 27 numbered singletons would
        # triple the listing's noise. They still appear once you type a letter.
        names = [name for name in command_names if _NUMBERED_COMMAND_RE.fullmatch(name) is None]
    else:
        names = list(command_names)
        numbered_names = [name for name in names if _NUMBERED_COMMAND_RE.fullmatch(name) is not None]
        if any(word.lower() in name.lower() for name in numbered_names):
            active_ids = set(active_state_ids())
            names = [name for name in names if _numbered_command_is_available(name, active_ids)]
    if include_repl_extra:
        names = names + list(REPL_EXTRA_COMMANDS)
    return names + _numbered_extensions(word, active_ids)


# ── Per-command argument candidates ──────────────────────────────────────


_DURATION_ARG_RE = re.compile(r"^(all|\d+[dwmy]?)$")


def _duration_already_present(args: list[str]) -> bool:
    """True when any arg parses as an export duration (mirrors parse_duration_arg).

    Implemented as a regex rather than importing ``export_utils`` because that
    module imports jdatetime — too heavy for a per-Tab check. Parity with the
    real parser is covered by a test.
    """
    return any(_DURATION_ARG_RE.fullmatch(arg.strip().lower()) for arg in args)


def _arg_candidates(base: str, args: list[str], command: str = "") -> list[str]:
    """Positional candidates for *base* given the command and committed *args*."""
    lowered_args = [arg.lower() for arg in args]

    if base == "et":
        # The optional text is free-form, but its completion can still surface
        # the categories currently injected by active numbered states. Keep
        # this narrow and require the slots named by the et command to be live.
        return _end_state_categories(command)

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

    # Other free-text commands (ee/ege/ln/v/t/...) and bare managers take no
    # completable positionals; universal flags are appended by suggest().
    return []


def suggest(
    tokens: list[str],
    word: str,
    command_names: list[str] | set[str] | tuple[str, ...],
    include_repl_extra: bool = True,
) -> list[str]:
    """Return completion candidates for a split line (see split_completion_line)."""
    names = list(command_names)
    if not tokens:
        return _match(_first_token_candidates(word, names, include_repl_extra), word)
    base = _base_command(tokens[0], set(names))
    if base is None:
        return []

    invalid_start_slot = base == "st" and re.fullmatch(r"st\d+", tokens[0].lower()) is not None
    if invalid_start_slot and not _start_command_is_available(tokens[0]):
        # An occupied or out-of-range slot cannot take categories or update
        # flags; leave only the universal help flags below.
        candidates = []
        command_flags = ()
    else:
        candidates = _arg_candidates(base, tokens[1:], tokens[0])
        command_flags = _COMMAND_DASH_FLAGS.get(base, ())
    for flag in command_flags:
        if flag not in candidates:
            candidates.append(flag)
    for flag in HELP_FLAGS:
        if flag not in candidates:
            candidates.append(flag)
    return _match(candidates, word)


def suggest_for_text(
    text: str,
    command_names: list[str] | set[str] | tuple[str, ...],
    include_repl_extra: bool = True,
) -> list[str]:
    """Convenience wrapper: split *text* (cursor at end) and suggest."""
    tokens, word = split_completion_line(text)
    return suggest(tokens, word, command_names, include_repl_extra)


# ── Inner-prompt completion ──────────────────────────────────────────────
# Structured prompts *inside* commands (viewers, selectors) get small static
# wordlists. Call sites import these lazily (function level) so
# non-interactive runs never pay for prompt_toolkit.

# Day view loop: ``\d*[np]`` navigation, ``m`` mode toggle, ``q`` quit
# (dates are free text and intentionally not completed).
DAY_VIEW_NAV = ("n", "p", "5n", "5p", "m", "q")

# Entry/search browsers: paging, ``d`` day-jump, ``q`` quit
# (numeric ids are values, completed by the eye from the listing).
BROWSER_NAV = ("n", "p", "5n", "5p", "d", "q")

# Travel-mode prayer slot selector (numbers, letters, names, cancel).
PRAYER_SLOT_CHOICES = ("1", "2", "3", "f", "d", "m", "fajr", "dhuhr", "maghrib", "n")
