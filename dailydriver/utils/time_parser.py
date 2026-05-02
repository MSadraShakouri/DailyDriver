# dailydriver/utils/time_parser.py
"""Unified time parsing helpers for all DailyDriver commands."""
import re
from datetime import datetime, timedelta


def parse_duration(s: str) -> int | None:
    """Parse a duration string like '30m', '1h', '1h15m'. Return minutes or None."""
    s = s.strip().lower()
    # "30m" or "30 min" or "30mins"
    m = re.match(r'^(\d+)\s*min(?:ute)?s?$', s)
    if m:
        return int(m.group(1))
    m = re.match(r'^(\d+)\s*m$', s)
    if m:
        return int(m.group(1))
    # "1h" or "1hour"
    m = re.match(r'^(\d+)\s*h(?:ou)?r?s?$', s)
    if m:
        return int(m.group(1)) * 60
    # "1h15m" or "1h15"
    m = re.match(r'^(\d+)\s*h\s*(?:(\d+)\s*m?)?$', s)
    if m:
        hours = int(m.group(1))
        mins = int(m.group(2)) if m.group(2) else 0
        return hours * 60 + mins
    return None


def parse_time(s: str, now: datetime, allow_future: bool = False) -> datetime | None:
    """Parse a time expression and return a datetime.
    Supports:
      - 'n' or 'now' → now
      - '-30' → 30 minutes ago
      - '14:00' → today at 14:00 (or yesterday if in the future, unless allow_future)
    """
    s = s.strip().lower()
    if s in ('n', 'now'):
        return now
    # offset: -30, -30m, -30min, -1h, -1hour, etc.
    m = re.match(r'^-(\d+)\s*(m(?:in(?:ute)?s?)?|h(?:ou)?r?s?)?$', s, re.IGNORECASE)
    if m:
        num = int(m.group(1))
        unit = (m.group(2) or '').lower()
        if unit.startswith('h'):
            minutes = num * 60
        else:
            minutes = num
        return now - timedelta(minutes=minutes)
    # HH:MM
    m = re.match(r'^(\d{1,2}):(\d{2})$', s)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour > 23 or minute > 59:
            return None
        dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if dt > now and not allow_future:
            dt -= timedelta(days=1)
        return dt
    # integer hour
    if s.isdigit():
        hour = int(s)
        if 0 <= hour <= 23:
            dt = now.replace(hour=hour, minute=0, second=0, microsecond=0)
            if dt > now and not allow_future:
                dt -= timedelta(days=1)
            return dt
    return None


def parse_time_range(args: list[str], now: datetime) -> tuple[datetime, datetime, int] | tuple[None, None, None]:
    """Parse start and end times, returning (start_dt, end_dt, duration_min).
    Accepts:
      - ['23:00', '07:15'] → start at 23:00, end 07:15 next day
      - ['23-7:15']         → compact form (also works if it's the only argument)
    """
    # If a single argument contains a hyphen, treat as compact form
    if len(args) == 1 and '-' in args[0]:
        parts = args[0].split('-')
        if len(parts) == 2:
            sleep_str, wake_str = parts[0], parts[1]
        else:
            return None, None, None
    elif len(args) == 2 and '-' in args[1]:
        parts = args[1].split('-')
        if len(parts) == 2:
            sleep_str, wake_str = parts[0], parts[1]
        else:
            return None, None, None
    elif len(args) >= 2:
        sleep_str, wake_str = args[0], args[1]
    else:
        return None, None, None

    sleep_dt = parse_time(sleep_str, now)
    if sleep_dt is None:
        return None, None, None
    wake_dt = parse_time(wake_str, now, allow_future=True)
    if wake_dt is None:
        return None, None, None

    if wake_dt <= sleep_dt:
        wake_dt += timedelta(days=1)

    duration = int((wake_dt - sleep_dt).total_seconds() / 60)
    return sleep_dt, wake_dt, duration


def parse_prayer_args(args: list[str]) -> dict:
    """Parse prayer command arguments and return a dict with keys:
    offset_min, explicit_time, jamaat_location, shak_count.
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
            # Try parsing as explicit time
            try:
                t = datetime.strptime(a, '%H:%M')
                result['explicit_time'] = t.hour * 60 + t.minute
            except ValueError:
                pass
            i += 1
    return result
