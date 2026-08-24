"""Single source of truth for command help.

Every command documents itself here once. Two consumers read this registry:

- ``-h`` / ``--help`` on any command renders that command's detailed entry
  (:func:`command_help`);
- the ``?`` / ``h`` summary lists every command grouped by area
  (:func:`build_summary`), so the overview can never drift from per-command help.

Entries are keyed by the command token as registered in the dispatcher. Aliases
point at their canonical command via ``alias_of`` so they share one entry.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HelpEntry:
    summary: str
    group: str
    usage: list[str] = field(default_factory=list)
    notes: str = ""
    alias_of: str | None = None


# Ordering of groups in the summary view.
GROUP_ORDER = [
    "Logging",
    "Prayer",
    "Events & Chaining",
    "Targets",
    "Qada",
    "Viewing & Summaries",
    "Calendar",
    "Tools & Setup",
    "Export",
    "Other",
]


HELP: dict[str, HelpEntry] = {
    # ── Logging ──
    "p": HelpEntry(
        summary="Log a prayer (Enter confirms)",
        group="Prayer",
        usage=[
            "p              current slot (auto-guessed)",
            "p -15          15 minutes before the fixed time",
            "p 05:30        explicitly at 05:30",
            "p j [location] with jamaat, optional location",
            "p s <count>    with a shak (doubt) count",
            "p q [time]     mark a past unlogged prayer as qada",
        ],
        notes="Prayer times are interpolated for Tehran. 'p q' logs at the current time by default.",
    ),
    "pray": HelpEntry(summary="Alias for p", group="Prayer", alias_of="p"),
    "s": HelpEntry(
        summary="Log sleep (bed + wake time)",
        group="Logging",
        usage=[
            "s 23:00 07:15  sleep at 23:00, wake at 07:15",
            "s 23-7:15      compact sleep-wake form",
            "s n 08:00      n = now (fell asleep now)",
            "s -30 08:00    fell asleep 30 minutes ago",
            "s ln           from last action to now",
        ],
        notes="Multiple sleep sessions per day are summed in the header.",
    ),
    "sleep": HelpEntry(summary="Alias for s", group="Logging", alias_of="s"),
    "nap": HelpEntry(
        summary="Log a nap (like sleep)",
        group="Logging",
        usage=[
            "nap 14:00 14:25  nap between two times",
            "nap 14-14:25     compact form",
            "nap l-14:00      from last action to 14:00",
        ],
        notes="Typing 'nap' alone prints usage. Naps appear as total nap time in the header.",
    ),
    "v": HelpEntry(
        summary="Log a void (scratchpad) entry",
        group="Logging",
        usage=["v <text>       unfiltered thought, kept out of the journal"],
        notes="No time parsing, categories, or keywords; does not update last_action.",
    ),
    "void": HelpEntry(summary="Alias for v", group="Logging", alias_of="v"),
    # ── Events & chaining ──
    "se": HelpEntry(summary="Start a running event timer", group="Events & Chaining", usage=["se"]),
    "ee": HelpEntry(
        summary="End the running event and log it",
        group="Events & Chaining",
        usage=["ee [text]      end event, log entry with optional description"],
    ),
    "ce": HelpEntry(summary="Cancel the running event", group="Events & Chaining", usage=["ce"]),
    "ln": HelpEntry(
        summary="Log an entry from the last action to now",
        group="Events & Chaining",
        usage=["ln [text]      chain: last action -> now"],
    ),
    "sge": HelpEntry(
        summary="Start a great event",
        group="Events & Chaining",
        usage=["sge <category> start a long-running great event"],
        notes="Active great events appear in the header and can absorb later entries.",
    ),
    "ege": HelpEntry(
        summary="End the great event and log it",
        group="Events & Chaining",
        usage=["ege [text]     end the great event, log entry"],
    ),
    "cge": HelpEntry(summary="Cancel the great event without logging", group="Events & Chaining", usage=["cge"]),
    "u": HelpEntry(
        summary="Refresh last_action to now (for chaining)",
        group="Events & Chaining",
        usage=["u"],
    ),
    "update": HelpEntry(summary="Alias for u", group="Events & Chaining", alias_of="u"),
    # ── Targets ──
    "targets": HelpEntry(
        summary="Open the targets manager (nazr + habits)",
        group="Targets",
        usage=[
            "targets                    open manager (all)",
            "nazr / habit               open manager filtered by kind",
            "<kind> log <name> <n>      log progress",
            "<kind> daily_total <name> <n>   set today's total",
            "<kind> counter_total <name> <n> log difference from counter",
            "<kind> counter_reset <name>     reset counter to 0",
        ],
        notes="Creation and editing happen inside the interactive manager.",
    ),
    "nazr": HelpEntry(summary="Finite goals manager + logging", group="Targets", alias_of="targets"),
    "habit": HelpEntry(summary="Indefinite habits manager + logging", group="Targets", alias_of="targets"),
    # ── Qada ──
    "qada": HelpEntry(
        summary="Missed-prayer & fasting backlog",
        group="Qada",
        usage=[
            "qada                    open the interactive manager",
            "qada log <slot|id> [n]  log prayer qada progress",
            "qada fasting yes        log today's fast",
            "qada fasting no         pause fasting for a day",
        ],
        notes="Targets and intervals are edited inside the manager.",
    ),
    # ── Viewing & summaries ──
    "day": HelpEntry(
        summary="Show a day view",
        group="Viewing & Summaries",
        usage=[
            "day                today's view",
            "day -1             yesterday",
            "day 1405-02-15     a specific Jalali date",
        ],
        notes="Inside: p/n navigate, 5n/5p jump, a date to go there, q to quit.",
    ),
    "today": HelpEntry(summary="Alias for day", group="Viewing & Summaries", alias_of="day"),
    "view": HelpEntry(
        summary="Browse journal entries",
        group="Viewing & Summaries",
        usage=[
            "view               all entries, newest first",
            "view <filter>      filter by category text",
        ],
        notes="Inside: n/p (or 5n/5p) navigate, an id edits, 'd <id>' opens that day.",
    ),
    "search": HelpEntry(
        summary="Full-text search with fuzzy boosts",
        group="Viewing & Summaries",
        usage=[
            "search <query>     text + time/date/category scoring",
            "search morning     time-of-day boost",
            "search yesterday   relative-date boost",
        ],
        notes="FTS5 with LIKE fallback; misspellings tolerated. n/p/5n paginate.",
    ),
    "recent": HelpEntry(summary="Show the last 5 journal entries", group="Viewing & Summaries", usage=["recent"]),
    "stats": HelpEntry(
        summary="Prayer / sleep / hygiene / category stats",
        group="Viewing & Summaries",
        usage=["stats"],
    ),
    # ── Calendar ──
    "cal": HelpEntry(
        summary="Month grid + upcoming events",
        group="Calendar",
        usage=[
            "cal                current month",
            "cal 6              month 6 of current year",
            "cal 6 1405         month 6 of year 1405",
        ],
    ),
    "year": HelpEntry(summary="Full-year grid (adaptive columns)", group="Calendar", usage=["year"]),
    "hijri": HelpEntry(
        summary="Show/adjust the Hijri date offset",
        group="Calendar",
        usage=["hijri              interactive offset selector (-2..+2)"],
    ),
    # ── Tools & setup ──
    "bd": HelpEntry(
        summary="Add a birthday (interactive)",
        group="Tools & Setup",
        usage=["bd                 prompts for name, date, reminder level"],
        notes="Interactive only: name, day, month, optional year and reminder level.",
    ),
    "birthdays": HelpEntry(
        summary="Manage the birthday list",
        group="Tools & Setup",
        usage=["birthdays          toggle reminders, add, or delete"],
    ),
    "t": HelpEntry(
        summary="Add an intention / to-do",
        group="Tools & Setup",
        usage=[
            "t                  interactive (deadline + duration)",
            "t <description>    quick add with description only",
        ],
    ),
    "hygiene": HelpEntry(
        summary="Manage hygiene intervals",
        group="Tools & Setup",
        usage=["hygiene            interactive manager (add/edit/delete)"],
    ),
    "travel": HelpEntry(
        summary="Travel mode (disable location features)",
        group="Tools & Setup",
        usage=[
            "travel             toggle travel mode",
            "travel on|off      set explicitly",
            "travel status      show current state",
        ],
    ),
    "daystart": HelpEntry(
        summary="Shift the day boundary hour",
        group="Tools & Setup",
        usage=[
            "daystart           show current day-start hour",
            "daystart <0-23>    set the day-start hour (default 4)",
        ],
    ),
    # ── Export ──
    "export": HelpEntry(
        summary="Export a chronological timeline",
        group="Export",
        usage=[
            "export 7d          last 7 days (Markdown)",
            "export 2w --txt    plain-text timeline",
            "export all         everything, no cutoff",
        ],
        notes="Journal, sleep, naps, prayers, qada, and target logs are interleaved.",
    ),
    "vexport": HelpEntry(
        summary="Export void entries",
        group="Export",
        usage=["vexport <duration|all>   export the void scratchpad"],
    ),
    # ── Other ──
    "q": HelpEntry(summary="Quit", group="Other", usage=["q"]),
    "?": HelpEntry(summary="Show this help summary", group="Other", usage=["?", "-h / --help on any command"]),
    "h": HelpEntry(summary="Alias for ?", group="Other", alias_of="?"),
}


def resolve(name: str) -> tuple[str, HelpEntry] | None:
    """Return the canonical (name, entry) for a command, following aliases."""
    entry = HELP.get(name)
    if entry is None:
        return None
    if entry.alias_of:
        canonical = entry.alias_of
        target = HELP.get(canonical)
        if target is not None:
            return canonical, target
    return name, entry


def command_help(name: str) -> list[str]:
    """Render the detailed help block for a single command as text lines."""
    resolved = resolve(name)
    if resolved is None:
        return [f"No help available for '{name}'."]
    canonical, entry = resolved
    lines = [f"{canonical} — {entry.summary}"]
    aliases = sorted(alias for alias, e in HELP.items() if e.alias_of == canonical)
    if aliases:
        lines.append(f"  aliases: {', '.join(aliases)}")
    if entry.usage:
        lines.append("")
        lines.append("Usage:")
        for usage in entry.usage:
            lines.append(f"  {usage}")
    if entry.notes:
        lines.append("")
        lines.append(entry.notes)
    return lines


def build_summary(command_names: list[str] | None = None) -> list[str]:
    """Render the grouped ``?`` summary from the registry.

    When *command_names* is given, only those registered commands are listed,
    keeping the summary in sync with what the dispatcher actually offers.
    """
    available = set(command_names) if command_names is not None else set(HELP)

    lines = ["═" * 52, "  DailyDriver — Command Summary", "═" * 52, ""]
    for group in GROUP_ORDER:
        rows: list[tuple[str, str]] = []
        for name, entry in HELP.items():
            if entry.group != group or entry.alias_of is not None:
                continue
            if name not in available:
                continue
            aliases = sorted(a for a, e in HELP.items() if e.alias_of == name and a in available)
            label = name if not aliases else f"{name} ({', '.join(aliases)})"
            rows.append((label, entry.summary))
        if not rows:
            continue
        lines.append(group)
        width = max(len(label) for label, _ in rows)
        for label, summary in rows:
            lines.append(f"  {label.ljust(width)}  {summary}")
        lines.append("")

    lines.append("Add -h or --help after any command for details (e.g. 'p -h').")
    return lines
