"""The ``city`` command: interactive manager for default city, schedule, override."""

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
from dailydriver.ui.terminal_ui import current_ui

_UPCOMING_PREVIEW = 5
_CANCEL_TOKENS = ("", "n", "q", "cancel")


def city_command(_cmd: str):
    """Open the interactive city manager (default, weekly schedule, override)."""
    with get_connection_cm(auto=False) as conn:
        _manager(conn)


def _manager(conn):
    while True:
        current_ui.print_line("")
        _print_status(conn)
        current_ui.print_line("")
        current_ui.print_line("  [1] Change city now")
        current_ui.print_line("  [2] Edit schedule")
        current_ui.print_line("  [3] Edit default city")
        current_ui.print_line("  [4] View/clear override")
        current_ui.print_line("  [q] Quit")
        choice = current_ui.prompt("city> ").strip().lower()
        if choice in ("q", "quit", ""):
            return
        if choice == "1":
            _change_city_now(conn)
        elif choice == "2":
            _edit_schedule(conn)
        elif choice == "3":
            _edit_default(conn)
        elif choice == "4":
            _view_override(conn)
        else:
            current_ui.print_line("Invalid choice.")


def _print_status(conn):
    now = datetime.now()
    info = resolve_city(conn, now)
    current_ui.print_line(f"Current city: {info.name} ({_reason_text(conn, info)})")

    rules = list_rules(conn)
    upcoming = []
    cursor = now
    for _ in range(_UPCOMING_PREVIEW):
        nxt = next_rule_start(rules, cursor)
        if nxt is None:
            break
        start, rule = nxt
        upcoming.append(f"{start.strftime('%a %d %b %H:%M')} -> {rule.city}")
        cursor = start + timedelta(minutes=1)
    if upcoming:
        current_ui.print_line("Upcoming transitions:")
        for line in upcoming:
            current_ui.print_line(f"  {line}")
    else:
        current_ui.print_line("No schedule rules (the default city applies).")


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


def _pick_city() -> str | None:
    names = sorted(load_registry())
    current_ui.print_line("Pick city:")
    for i, name in enumerate(names, 1):
        current_ui.print_line(f"  [{i}] {name}")
    current_ui.print_line("  [n] Cancel")
    choice = current_ui.prompt("> ").strip().lower()
    if choice in ("n", "cancel", ""):
        return None
    if choice.isdigit() and 1 <= int(choice) <= len(names):
        return names[int(choice) - 1]
    current_ui.print_line("Invalid choice.")
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
    choice = current_ui.prompt("> ").strip().lower()
    if choice in ("n", "cancel", ""):
        return None
    if choice == "1":
        return ("next_change", int(nxt[0].timestamp()) if nxt else None)
    if choice == "2":
        while True:
            raw = current_ui.prompt("Date & time (YYYY-MM-DD HH:MM, Enter=cancel): ").strip()
            if raw.lower() in _CANCEL_TOKENS:
                return None
            try:
                moment = datetime.strptime(raw, "%Y-%m-%d %H:%M")
            except ValueError:
                current_ui.print_line("✗ Use YYYY-MM-DD HH:MM (for example 2026-10-01 08:00)")
                continue
            return ("specific", int(moment.timestamp()))
    if choice == "3":
        return ("indefinite", None)
    current_ui.print_line("Invalid choice.")
    return None


def _change_city_now(conn):
    names = sorted(load_registry())
    default_name = city_state.get_default_city(conn)
    current_ui.print_line("Use which city?")
    for i, name in enumerate(names, 1):
        marker = " (default)" if name == default_name else ""
        current_ui.print_line(f"  [{i}] {name}{marker}")
    current_ui.print_line("  [d] Use the default city")
    current_ui.print_line("  [n] Cancel")
    choice = current_ui.prompt("> ").strip().lower()
    if choice in ("n", "cancel", ""):
        return
    if choice == "d":
        city = None
    elif choice.isdigit() and 1 <= int(choice) <= len(names):
        city = names[int(choice) - 1]
    else:
        current_ui.print_line("Invalid choice.")
        return

    duration = _pick_duration(conn)
    if duration is None:
        return
    mode, until_ts = duration
    city_state.set_override(conn, city, until_ts, mode)
    current_ui.print_line(f"Override set: {city or default_name} ({mode}).")


def _edit_schedule(conn):
    while True:
        rules = list_rules(conn)
        if rules:
            width = max(len(rule.city) for rule in rules)
            current_ui.print_line("Current rules:")
            for rule in rules:
                current_ui.print_line(
                    f"  [{rule.id}] {rule.city.ljust(width)}  {format_days(rule.days)}  "
                    f"{format_clock_minutes(rule.from_min)}-{format_clock_minutes(rule.to_min)}"
                )
        else:
            current_ui.print_line("No rules configured.")
        current_ui.print_line("  [a] Add rule   [e] Edit rule   [d] Delete rule   [q] Back")
        choice = current_ui.prompt("schedule> ").strip().lower()
        if choice in ("q", "quit", ""):
            return
        if choice == "a":
            _add_rule_flow(conn)
        elif choice == "e":
            _edit_rule_flow(conn, rules)
        elif choice == "d":
            _delete_rule_flow(conn, rules)
        else:
            current_ui.print_line("Invalid choice.")


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
    while True:
        raw = current_ui.prompt("Days (e.g. 0 2 / sat mon / 0-4 / all): ").strip()
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
    while True:
        raw = current_ui.prompt("Time range (e.g. 07:00-17:00): ").strip()
        if raw.lower() in _CANCEL_TOKENS:
            return None
        try:
            return _parse_range(raw)
        except RuleError as exc:
            current_ui.print_line(f"✗ {exc}")


def _describe_rule(rule_id: int, city: str, days, from_min: int, to_min: int) -> str:
    return (
        f"{city} — {format_days(days)} "
        f"{format_clock_minutes(from_min)}-{format_clock_minutes(to_min)} (id {rule_id})"
    )


def _add_rule_flow(conn):
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
    current_ui.print_line(f"Rule added: {_describe_rule(rule_id, city, days, from_min, to_min)}")


def _edit_rule_flow(conn, rules):
    if not rules:
        current_ui.print_line("No rules to edit.")
        return
    raw = current_ui.prompt("Rule id to edit: ").strip()
    if not raw.isdigit() or not any(rule.id == int(raw) for rule in rules):
        current_ui.print_line("Invalid rule id.")
        return
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
            update_rule(conn, int(raw), city, days, from_min, to_min)
        except RuleError as exc:
            current_ui.print_line(f"✗ {exc}")
            continue
        break
    current_ui.print_line(f"Rule updated: {_describe_rule(int(raw), city, days, from_min, to_min)}")


def _delete_rule_flow(conn, rules):
    if not rules:
        current_ui.print_line("No rules to delete.")
        return
    raw = current_ui.prompt("Rule id to delete: ").strip()
    if not raw.isdigit():
        current_ui.print_line("Invalid rule id.")
        return
    try:
        delete_rule(conn, int(raw))
    except RuleError as exc:
        current_ui.print_line(f"Cannot delete: {exc}")
        return
    current_ui.print_line("Rule deleted.")


def _edit_default(conn):
    city = _pick_city()
    if city is None:
        return
    city_state.set_default_city(conn, city)
    current_ui.print_line(f"Default city set to {city}.")


def _view_override(conn):
    state = city_state.get_state(conn)
    if state["override_mode"] is None:
        current_ui.print_line("No override active.")
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
