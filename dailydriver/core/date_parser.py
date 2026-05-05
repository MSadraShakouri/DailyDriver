import re
import jdatetime
from datetime import datetime, timedelta

# Map weekday names to Python weekday numbers (Monday=0 ... Sunday=6)
_WEEKDAYS = {
    'sat': 5, 'saturday': 5,
    'sun': 6, 'sunday': 6,
    'mon': 0, 'monday': 0,
    'tue': 1, 'tuesday': 1,
    'wed': 2, 'wednesday': 2,
    'thu': 3, 'thursday': 3,
    'fri': 4, 'friday': 4,
}

def _parse_date_jalali(s: str):
    """Try to parse a Jalali date YYYY/MM/DD or YYYY-MM-DD. Return Gregorian datetime with time 00:00."""
    m = re.search(r'(\d{4})\s*[-/]\s*(\d{1,2})\s*[-/]\s*(\d{1,2})', s)
    if not m:
        return None
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        jdate = jdatetime.date(y, mo, d)
        gdate = jdate.togregorian()
        return datetime(gdate.year, gdate.month, gdate.day, 0, 0, 0)
    except ValueError:
        return None

def _parse_relative_date(text: str, now: datetime):
    """Detect relative date expressions and return a datetime (or None)."""
    text = text.lower().strip()
    # yesterday/today/tomorrow
    if 'yesterday' in text:
        return (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    if 'today' in text:
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    if 'tomorrow' in text:
        return (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

    # last <weekday> / next <weekday> / <weekday>
    for name, wd in _WEEKDAYS.items():
        if f'last {name}' in text:
            days_ago = (now.weekday() - wd) % 7
            if days_ago == 0:
                days_ago = 7
            return (now - timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)
        if f'next {name}' in text:
            days_ahead = (wd - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            return (now + timedelta(days=days_ahead)).replace(hour=0, minute=0, second=0, microsecond=0)
        # plain <weekday> – nearest past
        if name in text and f'last {name}' not in text and f'next {name}' not in text:
            days_ago = (now.weekday() - wd) % 7
            if days_ago == 0:
                days_ago = 7
            return (now - timedelta(days=days_ago)).replace(hour=0, minute=0, second=0, microsecond=0)

    # N days ago / in N days
    m = re.search(r'(\d+)\s*days?\s*ago', text)
    if m:
        n = int(m.group(1))
        return (now - timedelta(days=n)).replace(hour=0, minute=0, second=0, microsecond=0)
    m = re.search(r'in\s+(\d+)\s*days?', text)
    if m:
        n = int(m.group(1))
        return (now + timedelta(days=n)).replace(hour=0, minute=0, second=0, microsecond=0)

    return None
