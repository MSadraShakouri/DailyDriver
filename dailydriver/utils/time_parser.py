# dailydriver/utils/time_parser.py
"""Unified time expression parser – single authority for all time input."""
import re
from datetime import datetime, timedelta
from typing import NamedTuple


class TimeInterpretation(NamedTuple):
    start: datetime
    end: datetime | None
    duration_minutes: int | None
    label: str
    priority: int  # lower = better


# ---------------------------------------------------------------------------
# 1. Tokenising helpers
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(
    r'^(\d+)\s*(?:h|hour|hours)?\s*(?:(\d+)\s*(?:m|min|mins|minute|minutes)?)?$',
    re.IGNORECASE,
)

_OFFSET_RE = re.compile(
    r'^-(\d+)\s*(m|min|mins|minute|minutes|h|hour|hours)?$',
    re.IGNORECASE,
)

_LAST_DURATION_RE = re.compile(
    r'^(?:last|l)\s*(\d+)\s*(m|min|mins|minute|minutes|h|hour|hours)?$',
    re.IGNORECASE,
)

_LAST_FORWARD_RE = re.compile(
    r'^(?:last|l)\s*\+\s*(\d+)\s*(m|min|mins|minute|minutes|h|hour|hours)?$',
    re.IGNORECASE,
)

_TIME_RE = re.compile(r'^(\d{1,2}):(\d{2})$')

_HOUR_RE = re.compile(r'^(\d{1,2})$')


def _parse_duration(token: str) -> int | None:
    """Return duration in minutes, or None if token is not a duration.
    Accepts: '30m', '30min', '30 mins', '1h', '2hour', '2hours',
    '1h30m', '1h 30m', bare numbers as minutes."""
    token = token.strip().lower()
    # 1h30m, 1h 30m
    m = re.match(r'^(\d+)\s*h\s*(\d+)\s*m(?:in(?:ute)?s?)?$', token)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    # 1h, 2hour, 2hours
    m = re.match(r'^(\d+)\s*h(?:ou)?r?s?$', token)
    if m:
        return int(m.group(1)) * 60
    # 30m, 30min, 30 mins
    m = re.match(r'^(\d+)\s*m(?:in(?:ute)?s?)?$', token)
    if m:
        return int(m.group(1))
    # bare number → minutes
    m = re.match(r'^(\d+)$', token)
    if m:
        return int(m.group(1))
    return None

def _parse_offset(token: str) -> int | None:
    """Return positive minutes for an offset like '-15', '-1h', or None."""
    token = token.strip().lower()
    m = _OFFSET_RE.match(token)
    if not m:
        return None
    num = int(m.group(1))
    unit = m.group(2) or 'm'
    if unit.startswith('h'):
        return num * 60
    return num


def _parse_last_duration(token: str) -> int | None:
    """Parse 'last5m', 'last 5 min', 'l5m' → minutes (range: start=now-num, end=now)."""
    token = token.strip().lower()
    m = _LAST_DURATION_RE.match(token)
    if not m:
        return None
    num = int(m.group(1))
    unit = m.group(2) or 'm'
    if unit.startswith('h'):
        return num * 60
    return num


def _parse_last_forward(token: str) -> int | None:
    """Parse 'l+5m', 'l+1h' → minutes (range: start=last, end=last+num)."""
    token = token.strip().lower()
    m = _LAST_FORWARD_RE.match(token)
    if not m:
        return None
    num = int(m.group(1))
    unit = m.group(2) or 'm'
    if unit.startswith('h'):
        return num * 60
    return num

def _tokenise(text: str) -> list[str]:
    """Split on whitespace, keep '--' as a token, and split compact dash ranges."""
    text = text.strip()
    # Step 1: protect '--' by replacing with a unique placeholder
    placeholder = '\x00DOUBLE_DASH\x00'
    text = text.replace('--', f' {placeholder} ')
    tokens = text.split()
    # Step 2: restore placeholder back to '--'
    tokens = [t if t != placeholder else '--' for t in tokens]

    new_tokens = []
    for token in tokens:
        if token == '--':
            # Keep as-is
            new_tokens.append(token)
        elif token.startswith('-'):
            # Offset token: may be '-15', '-15-n', etc.
            idx = token.find('-', 1)
            if idx != -1:
                new_tokens.append(token[:idx])
                new_tokens.append('-')
                new_tokens.append(token[idx+1:])
            else:
                new_tokens.append(token)
        elif '-' in token:
            # Compact range like '9:18-9:24'
            parts = token.split('-')
            if len(parts) == 2 and parts[0] and parts[1]:
                new_tokens.append(parts[0])
                new_tokens.append('-')
                new_tokens.append(parts[1])
            else:
                new_tokens.append(token)
        else:
            new_tokens.append(token)
    return new_tokens

# ---------------------------------------------------------------------------
# 2. Atom parsers (single time point)
# ---------------------------------------------------------------------------

def _time_atom(token: str, now: datetime, last_time: datetime | None) -> list[TimeInterpretation]:
    """
    Interpret a single token as a time point.
    Returns a list of interpretations (empty, 1, or 2 for AM/PM).
    """
    t = token.strip().lower()

    # Last-action time
    if t in ('l', 'last'):
        if last_time is None:
            return []  # No previous action
        return [TimeInterpretation(
            start=last_time, end=None, duration_minutes=None,
            label=f"last ({last_time.strftime('%H:%M')})", priority=2,
        )]

    # Now
    if t in ('n', 'now'):
        return [TimeInterpretation(
            start=now, end=None, duration_minutes=None,
            label="now", priority=2,
        )]

    # Offset: -15, -1h, -30m
    offset = _parse_offset(token)
    if offset is not None:
        start = now - timedelta(minutes=offset)
        return [TimeInterpretation(
            start=start, end=None, duration_minutes=None,
            label=f"{offset} min ago", priority=2,
        )]

    # 'ln' shorthand: from last to now
    if t == 'ln':
        if last_time is None:
            return []
        return [TimeInterpretation(
            start=last_time, end=now,
            duration_minutes=int((now - last_time).total_seconds() // 60),
            label=f"last → now ({last_time.strftime('%H:%M')} → {now.strftime('%H:%M')})",
            priority=1,
        )]

    # 'last5m', 'l5m', 'l+5m', 'l+1h'
    last_dur = _parse_last_duration(token)
    if last_dur is not None:
        start = now - timedelta(minutes=last_dur)
        return [TimeInterpretation(
            start=start, end=now,
            duration_minutes=last_dur,
            label=f"last {last_dur}m ({start.strftime('%H:%M')} → {now.strftime('%H:%M')})",
            priority=1,
        )]

    last_fwd = _parse_last_forward(token)
    if last_fwd is not None:
        if last_time is None:
            return []
        end = last_time + timedelta(minutes=last_fwd)
        return [TimeInterpretation(
            start=last_time, end=end,
            duration_minutes=last_fwd,
            label=f"last+{last_fwd}m ({last_time.strftime('%H:%M')} → {end.strftime('%H:%M')})",
            priority=1,
        )]

    # HH:MM
    m = _TIME_RE.match(token)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour > 23 or minute > 59:
            return []
        results = []
        for h in _candidate_hours(hour, now):
            start = now.replace(hour=h, minute=minute, second=0, microsecond=0)
            if start > now:
                start -= timedelta(days=1)
            results.append(TimeInterpretation(
                start=start, end=None, duration_minutes=None,
                label=start.strftime('%H:%M'), priority=2,
            ))
        # Sort closest to now first
        results.sort(key=lambda r: abs((r.start - now).total_seconds()))
        return results

    # Bare hour (only valid if it looks like part of a range; here we still return it)
    m = _HOUR_RE.match(token)
    if m:
        hour = int(m.group(1))
        if hour > 23:
            return []
        results = []
        for h in _candidate_hours(hour, now):
            start = now.replace(hour=h, minute=0, second=0, microsecond=0)
            if start > now:
                start -= timedelta(days=1)
            results.append(TimeInterpretation(
                start=start, end=None, duration_minutes=None,
                label=f"{h:02d}:00", priority=3,  # low priority, ambiguous
            ))
        results.sort(key=lambda r: abs((r.start - now).total_seconds()))
        return results

    return []


def _candidate_hours(hour: int, now: datetime) -> list[int]:
    """Return candidate hours for AM/PM disambiguation.
    If hour >= 13, only 24h; otherwise both AM and PM if they differ.
    """
    if hour > 12:
        return [hour]
    candidates = [hour]
    if hour + 12 <= 23:
        candidates.append(hour + 12)
    # Filter to those that could be today or yesterday
    return candidates


# ---------------------------------------------------------------------------
# 3. Main parser
# ---------------------------------------------------------------------------

def parse_time_expressions(
    text: str,
    now: datetime,
    last_time: datetime | None = None,
    mode: str = "optional",
) -> list[TimeInterpretation]:
    """Parse a time expression from *text*.
    Returns a list of TimeInterpretation, sorted best-first.
    *mode* can be 'optional', 'required', or 'no_duration' (used by callers).
    """
    if not text.strip():
        return []

    tokens = _tokenise(text)
    n = len(tokens)

    # ---------- double-dash range: START -- OFFSET ----------
    for i in range(n - 1):
        if tokens[i + 1] == '--' and i + 2 < n:
            left_atoms = _time_atom(tokens[i], now, last_time)
            offset_min = _parse_duration(tokens[i + 2])
            if offset_min is None:
                # maybe it's a bare number
                if tokens[i + 2].isdigit():
                    offset_min = int(tokens[i + 2])
                else:
                    continue
            for left in left_atoms:
                end = now - timedelta(minutes=offset_min)
                if end <= left.start:
                    continue
                dur = int((end - left.start).total_seconds() // 60)
                label = f"{left.start.strftime('%H:%M')} → {end.strftime('%H:%M')} ({dur}m)"
                return [TimeInterpretation(
                    start=left.start, end=end, duration_minutes=dur,
                    label=label, priority=1,
                )]

    # ---------- single-dash range: START - END ----------
    for i in range(n - 1):
        if tokens[i + 1] == '-' and i + 2 < n:
            left_atoms = _time_atom(tokens[i], now, last_time)
            right_atoms = _time_atom(tokens[i + 2], now, last_time)
            results = []
            for left in left_atoms:
                for right in right_atoms:
                    end = right.start
                    if end <= left.start:
                        end += timedelta(days=1)
                    dur = int((end - left.start).total_seconds() // 60)
                    label = f"{left.start.strftime('%H:%M')} → {end.strftime('%H:%M')} ({dur}m)"
                    results.append(TimeInterpretation(
                        start=left.start, end=end, duration_minutes=dur,
                        label=label, priority=1,
                    ))
            if results:
                results.sort(key=lambda r: abs((r.start - now).total_seconds()))
                return results

    # ---------- single atom ----------
    atoms = []
    for token in tokens:
        if token in ('-', '--', '+'):
            continue
        atoms.extend(_time_atom(token, now, last_time))
    if atoms:
        atoms.sort(key=lambda r: abs((r.start - now).total_seconds()))
        return atoms

    return []

def parse_prayer_args(args: list[str]) -> dict:
    """Parse prayer command arguments – kept for compatibility.
    Returns dict with keys: offset_min, explicit_time, jamaat_location, shak_count.
    """
    result = {
        'offset_min': None,
        'explicit_time': None,
        'jamaat_location': None,
        'shak_count': 0,
    }
    i = 0
    while i < len(args):
        a = args[i]
        if a.startswith('-') and a[1:].isdigit():
            result['offset_min'] = int(a[1:])
            i += 1
        elif a.lower() == 'j':
            if i + 1 < len(args) and not args[i+1].startswith('-') and args[i+1].lower() not in ('j', 's'):
                result['jamaat_location'] = args[i+1]
                i += 2
            else:
                result['jamaat_location'] = ''
                i += 1
        elif a.lower() == 's':
            if i + 1 < len(args) and args[i+1].isdigit():
                result['shak_count'] = int(args[i+1])
                i += 2
            else:
                i += 1
        else:
            try:
                t = datetime.strptime(a, '%H:%M')
                result['explicit_time'] = t.hour * 60 + t.minute
            except ValueError:
                pass
            i += 1
    return result
