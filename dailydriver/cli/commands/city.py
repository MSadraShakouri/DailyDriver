"""The ``city`` command: interactive manager for default city, schedule, override.

Follows the house manager style (qada/hygiene): clear + app header each loop,
table body via ``spread_line``, one-line command guides, a bare ``>`` prompt,
a boxed ``?`` help screen, and a ``Press Enter to continue.`` pause after
every message so nothing is wiped by the next redraw.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from dailydriver.core.database import get_connection_cm
from dailydriver.core.location import state as city_state
from dailydriver.core.location.registry import load_registry
from dailydriver.core.location.resolver import resolve_city
from dailydriver.core.location.rules import (
    RuleError,
    add_rule,
    delete_rule,
    format_clock_minutes,
    format_days,
    list_rules,
    next_rule_start,
    normalize_days,
    parse_clock_minutes,
    update_rule,
    validate_window,
)
from dailydriver.display.display_utils import get_width, spread_line
from dailydriver.display.header import build_header_data
from dailydriver.display.header_renderer import print_header
from dailydriver.ui.terminal_ui import current_ui

_UPCOMING_PREVIEW = 3
_CANCEL_TOKENS = ("", "n", "q", "cancel")
_NARROW_WIDTH = 64


def _narrow() -> bool:
    return get_width() < _NARROW_WIDTH


def _guide(commands: list[str]) -> None:
    """Command help: justified spread on wide terminals, greedily packed
    lines on narrow ones (merge short entries instead of stacking)."""
    tw = get_width()
    current_ui.print_line()
    if _narrow():
        line = "  "
        for command in commands:
            candidate = f"{line}  {command}" if line.strip() else f"  {command}"
            if len(candidate) <= tw:
                line = candidate
            else:
                current_ui.print_line(line)
                line = f"  {command}"
        current_ui.print_line(line)
    elif len(commands) > 4:
        current_ui.print_line(spread_line(commands[:3], width=tw, margins=1 / 8))
        current_ui.print_line(spread_line(commands[3:], width=tw, margins=1 / 8))
    else:
        current_ui.print_line(spread_line(commands, width=tw, margins=1 / 8))
    current_ui.print_line()


def city_command(_cmd: str):
    """Open the interactive city manager (default, weekly schedule, override)."""
    with get_connection_cm(auto=False) as conn:
        _manager(conn)


def _manager(conn):
    while True:
        current_ui.clear()
        print_header(build_header_data())

        _print_status(conn)
        current_ui.print_line()
        _print_transitions(conn)
        current_ui.print_line()
        _print_rules_table(conn)
        _guide(["(c)hange now", "(s)chedule", "(d)efault city", "(o)verride", "(?)help", "(q)uit"])
        choice = current_ui.prompt("> ").strip().lower()

        if choice in ("q", "quit", ""):
            return
        if choice == "?":
            _show_help()
            current_ui.prompt("Press Enter to continue.")
        elif choice == "c":
            _change_city_now(conn)
        elif choice == "s":
            _edit_schedule(conn)
        elif choice == "d":
            _edit_default(conn)
        elif choice == "o":
            _view_override(conn)
        else:
            current_ui.print_line("Unknown command. Type ? for help.")
            current_ui.prompt("Press Enter to continue.")


def _print_status(conn):
    now = datetime.now()
    info = resolve_city(conn, now)
    reason = _reason_text(conn, info)
    text = f"  Current city: {info.name} ({reason})"
    if len(text) <= get_width():
        current_ui.print_line(text)
    else:
        # Keep every line inside the terminal: reason moves to its own line.
        current_ui.print_line(f"  Current city: {info.name}")
        current_ui.print_line(f"  ({reason})")


def _print_transitions(conn):
    rules = list_rules(conn)
    upcoming = []
    cursor = datetime.now()
    for _ in range(_UPCOMING_PREVIEW):
        nxt = next_rule_start(rules, cursor)
        if nxt is None:
            break
        start, rule = nxt
        upcoming.append(f"{start.strftime('%a %d %b %H:%M')} -> {rule.city}")
        cursor = start + timedelta(minutes=1)

    if not upcoming:
        current_ui.print_line("  No schedule rules (the default city applies).")
        return
    for line in upcoming:
        current_ui.print_line(f"  {line}")


def _print_rules_table(conn):
    """Render the rules table in the hygiene-manager column style."""
    rules = list_rules(conn)
    if not rules:
        return

    rows = [
        {
            "city": rule.city,
            "days": format_days(rule.days),
            "time": f"{format_clock_minutes(rule.from_min)}-{format_clock_minutes(rule.to_min)}",
        }
        for rule in rules
    ]
    max_city = max(len("City"), max(len(r["city"]) for r in rows))
    max_days = max(len("Days"), max(len(r["days"]) for r in rows))

    tw = get_width()
    current_ui.print_line(
        spread_line(["    " + "City".ljust(max_city), "Days".ljust(max_days), "Time "], width=tw, margins=0)
    )
    current_ui.print_line("─" * tw)
    for i, r in enumerate(rows, 1):
        current_ui.print_line(
            spread_line(
                [f" {i:>2} {r['city'].ljust(max_city)}", r["days"].ljust(max_days), r["time"] + " "],
                width=tw,
                margins=0,
            )
        )


def _reason_text(conn, info) -> str:
    if info.reason == "travel":
        return "travel mode"
    state = city_state.get_state(conn)
    if info.reason == "override":
        city_desc = info.name if state["override_city"] else f"{info.name} (default city)"
        if state["override_mode"] == "indefinite" or state["override_until"] is None:
            return f"override until cleared: {city_desc}"
        until = datetime.fromtimestamp(state["override_until"])
        return f"override until {until.strftime('%a %H:%M')}: {city_desc}"
    if info.reason == "schedule":
        until = f", until {info.until.strftime('%H:%M')}" if info.until else ""
        return f"schedule{until}"
    return "default"


_HELP_ROWS = [
    "c   Change city now (sets the override)",
    "s   Edit the weekly schedule",
    "d   Set the default city",
    "o   View/clear the override",
    "?   Show this help",
    "q   Quit manager",
]


def _show_help():
    current_ui.print_line()
    if _narrow():
        current_ui.print_line("  City Manager Help")
        for row in _HELP_ROWS:
            current_ui.print_line(f"  {row}")
        return
    bar = "─" * 50
    current_ui.print_line(f"┌─ City Manager Help {bar}┐")
    for row in _HELP_ROWS:
        current_ui.print_line(f"│ {row.ljust(66)}│")
    current_ui.print_line(f"└{bar + '─' * 20}┘")


def _pick_city() -> str | None:
    names = sorted(load_registry())
    current_ui.print_line("Pick city:")
    for i, name in enumerate(names, 1):
        current_ui.print_line(f"  [{i}] {name}")
    current_ui.print_line("  [n] Cancel")
    choice = current_ui.prompt(f"City (1-{len(names)}, Enter=cancel): ").strip().lower()
    if choice in _CANCEL_TOKENS:
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(names):
        return names[int(choice) - 1]
    current_ui.print_line("Invalid choice.")
    current_ui.prompt("Press Enter to continue.")
    return None


def _pick_duration(conn):
    """Return (mode, until_ts) or None when cancelled."""
    current_ui.print_line("Until when?")
    nxt = next_rule_start(list_rules(conn), datetime.now())
    next_desc = nxt[0].strftime("%a %H:%M") if nxt else "no rules found"
    current_ui.print_line(f"  [1] Next schedule change ({next_desc})")
    current_ui.print_line("  [2] Specific date & time (YYYY-MM-DD HH:MM)")
    current_ui.print_line("  [3] Indefinitely (until I clear it)")
    current_ui.print_line("  [n] Cancel")
    choice = current_ui.prompt("Duration (1-3, Enter=cancel): ").strip().lower()
    if choice in _CANCEL_TOKENS:
        return None
    if choice == "1":
        return ("next_change", int(nxt[0].timestamp()) if nxt else None)
    if choice == "2":
        while True:
            raw = current_ui.prompt("Date & time (Enter=cancel): ").strip()
            if raw.lower() in _CANCEL_TOKENS:
                return None
            try:
                moment = datetime.strptime(raw, "%Y-%m-%d %H:%M")
            except ValueError:
                current_ui.print_line("✗ Use YYYY-MM-DD HH:MM (e.g. 2026-10-01 08:00)")
                continue
            return ("specific", int(moment.timestamp()))
    if choice == "3":
        return ("indefinite", None)
    current_ui.print_line("Invalid choice.")
    current_ui.prompt("Press Enter to continue.")
    return None


def _change_city_now(conn):
    current_ui.print_line()
    current_ui.print_line("─── Change City Now ───")
    names = sorted(load_registry())
    default_name = city_state.get_default_city(conn)
    for i, name in enumerate(names, 1):
        marker = " (default)" if name == default_name else ""
        current_ui.print_line(f"  [{i}] {name}{marker}")
    current_ui.print_line("  [d] Use the default city")
    current_ui.print_line("  [n] Cancel")
    choice = current_ui.prompt("> ").strip().lower()
    if choice in _CANCEL_TOKENS:
        return
    if choice == "d":
        city = None
    elif choice.isdigit() and 1 <= int(choice) <= len(names):
        city = names[int(choice) - 1]
    else:
        current_ui.print_line("Invalid choice.")
        current_ui.prompt("Press Enter to continue.")
        return

    duration = _pick_duration(conn)
    if duration is None:
        return
    mode, until_ts = duration
    city_state.set_override(conn, city, until_ts, mode)
    current_ui.print_line(f"Override set: {city or default_name} ({mode}).")
    current_ui.prompt("Press Enter to continue.")


def _edit_schedule(conn):
    while True:
        current_ui.clear()
        print_header(build_header_data())
        current_ui.print_line("  Weekly schedule")
        current_ui.print_line()
        rules = list_rules(conn)
        if rules:
            _print_rules_table(conn)
        else:
            current_ui.print_line("  No rules configured.")
        current_ui.print_line("  (the default city applies outside rule windows)")
        _guide(["a add rule", "e <#> edit rule", "d <#> delete rule", "b back"])
        choice = current_ui.prompt("> ").strip().lower()

        if choice in ("b", "back", "q", ""):
            return
        if choice == "a":
            _add_rule_flow(conn)
        elif choice == "e":
            _edit_rule_flow(conn, rules, None)
        elif choice.startswith("e "):
            _edit_rule_flow(conn, rules, choice[2:].strip())
        elif choice == "d":
            _delete_rule_flow(conn, rules, None)
        elif choice.startswith("d "):
            _delete_rule_flow(conn, rules, choice[2:].strip())
        else:
            current_ui.print_line("Unknown command. Type ? for help.")
            current_ui.prompt("Press Enter to continue.")


def _parse_range(raw: str) -> tuple[int, int]:
    normalized = raw.lower().replace("–", "-").replace("—", "-").replace(" to ", "-")
    parts = [part for part in normalized.split("-") if part.strip()]
    if len(parts) != 2:
        raise RuleError("Use HH:MM-HH:MM (for example 07:00-17:00)")
    from_min, to_min = parse_clock_minutes(parts[0]), parse_clock_minutes(parts[1])
    validate_window(from_min, to_min)
    return from_min, to_min


def _prompt_days() -> tuple[int, ...] | None:
    """Prompt until the days parse; None means cancelled."""
    current_ui.print_line("  e.g. '0 2'  'sat mon'  '0-4'  'all'")
    while True:
        raw = current_ui.prompt("Days (Enter=cancel): ").strip()
        if raw.lower() in _CANCEL_TOKENS:
            return None
        try:
            days = normalize_days(raw)
        except RuleError as exc:
            current_ui.print_line(f"✗ {exc}")
            current_ui.print_line("  0=Sat  1=Sun  2=Mon  3=Tue  4=Wed  5=Thu  6=Fri")
            continue
        current_ui.print_line(f"  -> {format_days(days)}")
        return days


def _prompt_time_range() -> tuple[int, int] | None:
    """Prompt until the time range parses; None means cancelled."""
    current_ui.print_line("  e.g. 07:00-17:00 (or '7:00 to 12:00')")
    while True:
        raw = current_ui.prompt("Time range (Enter=cancel): ").strip()
        if raw.lower() in _CANCEL_TOKENS:
            return None
        try:
            return _parse_range(raw)
        except RuleError as exc:
            current_ui.print_line(f"✗ {exc}")


def _describe_rule(city: str, days, from_min: int, to_min: int) -> str:
    return f"{city} — {format_days(days)} {format_clock_minutes(from_min)}-{format_clock_minutes(to_min)}"


def _add_rule_flow(conn):
    current_ui.print_line()
    current_ui.print_line("─── Add Rule ───")
    city = _pick_city()
    if city is None:
        return
    days = _prompt_days()
    if days is None:
        return
    while True:
        window = _prompt_time_range()
        if window is None:
            return
        from_min, to_min = window
        try:
            rule_id = add_rule(conn, city, days, from_min, to_min)
        except RuleError as exc:
            # Conflicts and shape errors re-prompt only the time range; the
            # city and days already entered are kept.
            current_ui.print_line(f"✗ {exc}")
            continue
        break
    current_ui.print_line(f"Rule added: {_describe_rule(city, days, from_min, to_min)}")
    current_ui.prompt("Press Enter to continue.")


def _edit_rule_flow(conn, rules, arg: str | None):
    if not rules:
        current_ui.print_line("No rules to edit.")
        current_ui.prompt("Press Enter to continue.")
        return
    raw = arg if arg is not None else current_ui.prompt("Rule number to edit: ").strip()
    row = rules[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(rules) else None
    if row is None:
        current_ui.print_line("Usage: e <#> — no rule with that number.")
        current_ui.prompt("Press Enter to continue.")
        return
    current_ui.print_line()
    current_ui.print_line("─── Edit Rule ───")
    city = _pick_city()
    if city is None:
        return
    days = _prompt_days()
    if days is None:
        return
    while True:
        window = _prompt_time_range()
        if window is None:
            return
        from_min, to_min = window
        try:
            update_rule(conn, row.id, city, days, from_min, to_min)
        except RuleError as exc:
            current_ui.print_line(f"✗ {exc}")
            continue
        break
    current_ui.print_line(f"Rule updated: {_describe_rule(city, days, from_min, to_min)}")
    current_ui.prompt("Press Enter to continue.")


def _delete_rule_flow(conn, rules, arg: str | None):
    if not rules:
        current_ui.print_line("No rules to delete.")
        current_ui.prompt("Press Enter to continue.")
        return
    raw = arg if arg is not None else current_ui.prompt("Rule number to delete: ").strip()
    row = rules[int(raw) - 1] if raw.isdigit() and 1 <= int(raw) <= len(rules) else None
    if row is None:
        current_ui.print_line("Usage: d <#> — no rule with that number.")
        current_ui.prompt("Press Enter to continue.")
        return
    try:
        delete_rule(conn, row.id)
    except RuleError as exc:
        current_ui.print_line(f"Cannot delete: {exc}")
        current_ui.prompt("Press Enter to continue.")
        return
    current_ui.print_line("Rule deleted.")
    current_ui.prompt("Press Enter to continue.")


def _edit_default(conn):
    current_ui.print_line("\n─── Default City ───")
    city = _pick_city()
    if city is None:
        return
    city_state.set_default_city(conn, city)
    current_ui.print_line(f"Default city set to {city}.")
    current_ui.prompt("Press Enter to continue.")


def _view_override(conn):
    state = city_state.get_state(conn)
    if state["override_mode"] is None:
        current_ui.print_line("No override active.")
        current_ui.prompt("Press Enter to continue.")
        return
    city_desc = state["override_city"] or f"{state['default_city']} (default city)"
    if state["override_until"] is not None:
        until = f"until {datetime.fromtimestamp(state['override_until']).strftime('%a %H:%M')}"
    else:
        until = "until cleared"
    current_ui.print_line(f"Override: {city_desc} ({state['override_mode']}, {until})")
    if current_ui.confirm("Clear the override?", default_yes=False):
        city_state.clear_override(conn)
        current_ui.print_line("Override cleared.")
    current_ui.prompt("Press Enter to continue.")
