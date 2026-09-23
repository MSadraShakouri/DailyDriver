"""Weekly city-rule storage, validation, and transition computation.

Rules map weekday + time-of-day ranges to a city.  ``days`` is stored as a
JSON list of weekday numbers with Saturday = 0 through Friday = 6 (the
Iranian week).  Ranges are inclusive at ``from_min`` and exclusive at
``to_min``, so adjacent rules on one day are valid; overnight windows are
not supported and ``from_min < to_min`` is enforced.  Overlapping rules on
a shared day are rejected at save time; gaps fall through to the default
city.  Schedule edits take effect immediately.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

MINUTES_PER_DAY = 24 * 60
WEEKDAY_NAMES = ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]

_ALL_DAYS_TOKENS = ("all", "daily", "*")


class RuleError(ValueError):
    """Raised when a rule's shape or content is invalid."""


class RuleConflict(RuleError):
    """Raised when a new or updated rule overlaps an existing one."""


@dataclass(frozen=True)
class Rule:
    id: int
    city: str
    days: tuple[int, ...]
    from_min: int
    to_min: int

    def covers(self, weekday: int, minute: int) -> bool:
        """Inclusive from, exclusive to: 8:00-18:00 means ends at 17:59."""
        return weekday in self.days and self.from_min <= minute < self.to_min


def iranian_weekday(day: date) -> int:
    """Map a Python date to the Iranian week: Saturday = 0 .. Friday = 6."""
    return (day.weekday() + 2) % 7


def normalize_days(days) -> tuple[int, ...]:
    """Accept 'all', one int, or an iterable/'0,3,4' string of weekday ints."""
    if isinstance(days, str):
        text = days.strip().lower()
        if text in _ALL_DAYS_TOKENS:
            return tuple(range(7))
        try:
            days = [int(part) for part in text.replace(" ", "").split(",") if part]
        except ValueError as exc:
            raise RuleError(f"Invalid days: {days!r}") from exc
    if isinstance(days, int):
        days = [days]
    try:
        cleaned = sorted({int(d) for d in days})
    except (TypeError, ValueError) as exc:
        raise RuleError(f"Invalid days: {days!r}") from exc
    if not cleaned or any(d < 0 or d > 6 for d in cleaned):
        raise RuleError("Days must be weekday numbers 0 (Sat) through 6 (Fri)")
    return tuple(cleaned)


def parse_clock_minutes(text: str) -> int:
    """Parse ``HH:MM`` / ``H:MM`` / ``HHMM`` into minutes since midnight."""
    cleaned = str(text).strip().replace(":", "")
    if not cleaned.isdigit() or not 1 <= len(cleaned) <= 4:
        raise RuleError(f"Invalid time: {text!r} (use HH:MM)")
    padded = cleaned.zfill(4)
    hour, minute = int(padded[:-2]), int(padded[-2:])
    if not (0 <= hour <= 24 and 0 <= minute < 60) or (hour == 24 and minute != 0):
        raise RuleError(f"Invalid time: {text!r} (use HH:MM)")
    return hour * 60 + minute


def format_clock_minutes(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


def validate_window(from_min: int, to_min: int) -> None:
    if not (0 <= from_min < to_min <= MINUTES_PER_DAY):
        raise RuleError("Rule windows must satisfy 0:00 <= from < to <= 24:00 (no overnight windows)")


def rules_overlap(days, from_min: int, to_min: int, other: Rule) -> bool:
    return any(day in other.days for day in days) and from_min < other.to_min and other.from_min < to_min


def list_rules(conn) -> list[Rule]:
    rows = conn.execute(
        "SELECT id, city, days, from_min, to_min FROM city_rules ORDER BY from_min, id"
    ).fetchall()
    return [
        Rule(row["id"], row["city"], tuple(json.loads(row["days"])), row["from_min"], row["to_min"])
        for row in rows
    ]


def _reject_conflicts(conn, rule_id, city, days, from_min, to_min) -> None:
    for existing in list_rules(conn):
        if existing.id != rule_id and rules_overlap(days, from_min, to_min, existing):
            raise RuleConflict(
                f"Overlaps the existing {existing.city} rule "
                f"({format_clock_minutes(existing.from_min)}-{format_clock_minutes(existing.to_min)} "
                f"on {', '.join(WEEKDAY_NAMES[d] for d in existing.days)})"
            )


def add_rule(conn, city: str, days, from_min: int, to_min: int) -> int:
    """Validate and insert one rule; raise RuleConflict on overlap."""
    days = normalize_days(days)
    validate_window(from_min, to_min)
    _reject_conflicts(conn, None, city, days, from_min, to_min)
    cur = conn.execute(
        "INSERT INTO city_rules (city, days, from_min, to_min) VALUES (?, ?, ?, ?)",
        (city, json.dumps(list(days)), int(from_min), int(to_min)),
    )
    conn.commit()
    return cur.lastrowid


def update_rule(conn, rule_id: int, city: str, days, from_min: int, to_min: int) -> None:
    days = normalize_days(days)
    validate_window(from_min, to_min)
    _reject_conflicts(conn, rule_id, city, days, from_min, to_min)
    cur = conn.execute(
        "UPDATE city_rules SET city = ?, days = ?, from_min = ?, to_min = ? WHERE id = ?",
        (city, json.dumps(list(days)), int(from_min), int(to_min), rule_id),
    )
    if cur.rowcount == 0:
        raise RuleError(f"No rule with id {rule_id}")
    conn.commit()


def delete_rule(conn, rule_id: int) -> None:
    cur = conn.execute("DELETE FROM city_rules WHERE id = ?", (rule_id,))
    if cur.rowcount == 0:
        raise RuleError(f"No rule with id {rule_id}")
    conn.commit()


def active_rule(rules, weekday: int, minute: int) -> Rule | None:
    for rule in rules:
        if rule.covers(weekday, minute):
            return rule
    return None


def next_rule_start(rules, now: datetime) -> tuple[datetime, Rule] | None:
    """Return the next (start, rule) strictly after ``now``, or None."""
    best: tuple[datetime, Rule] | None = None
    for rule in rules:
        for offset in range(8):
            day = (now + timedelta(days=offset)).date()
            if iranian_weekday(day) not in rule.days:
                continue
            start = datetime.combine(day, time()) + timedelta(minutes=rule.from_min)
            if start <= now:
                continue  # e.g. today's start already passed
            if best is None or start < best[0]:
                best = (start, rule)
            break  # the first matching weekday gives this rule's earliest start
    return best
