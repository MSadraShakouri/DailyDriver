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

def _parse_time_string(s: str, now: datetime):
    """Parse a HH:MM time string and return a datetime for today, or None."""
    m = re.match(r'^(\d{1,2}):(\d{2})$', s)
    if not m:
        return None
    h, mins = int(m.group(1)), int(m.group(2))
    if h > 23 or mins > 59:
        return None
    return now.replace(hour=h, minute=mins, second=0, microsecond=0)

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

def extract_time(text: str):
    """
    Scan the whole text for any time/date expressions.
    Returns (started_at_timestamp, duration_minutes) or (None, None).
    """
    now = datetime.now()
    text_clean = text.strip()

    # ---------- 1. Offset: -30m, -1h (anywhere in text) ----------
    m = re.search(r'-(\d+)\s*[mM](?!\w)', text_clean)
    if not m:
        m = re.search(r'-(\d+)\s*[hH](?!\w)', text_clean)
    if m:
        num = int(m.group(1))
        unit = 'h' if 'h' in m.group(0).lower() else 'm'
        if unit == 'h':
            return int((now - timedelta(hours=num)).timestamp()), None
        else:
            return int((now - timedelta(minutes=num)).timestamp()), None

    # ---------- 2. Time range like 17-02 (anywhere) ----------
    range_match = re.search(r'(\d{1,2})\s*-\s*(\d{1,2})(?::(\d{2}))?', text_clean)
    if range_match:
        try:
            h1, h2 = int(range_match.group(1)), int(range_match.group(2))
            m2 = int(range_match.group(3)) if range_match.group(3) else 0
            if 0 <= h1 <= 23 and 0 <= h2 <= 23:
                start = now.replace(hour=h1, minute=0, second=0, microsecond=0)
                end = now.replace(hour=h2, minute=m2, second=0, microsecond=0)
                if end <= start:
                    end += timedelta(days=1)
                duration = int((end - start).total_seconds() / 60)
                return int(start.timestamp()), duration
        except:
            pass

    # ---------- 2b. Time to now: 13-n, 4:30-n ----------
    m = re.search(r'(\d{1,2})(?::(\d{2}))?\s*-\s*n\b', text_clean)
    if m:
        h1 = int(m.group(1))
        m1 = int(m.group(2)) if m.group(2) else 0
        if 0 <= h1 <= 23 and 0 <= m1 <= 59:
            start = now.replace(hour=h1, minute=m1, second=0, microsecond=0)
            if start > now:
                start -= timedelta(days=1)      # start is earlier same day (yesterday if future)
            duration = int((now - start).total_seconds() / 60)
            return int(start.timestamp()), duration

    # ---------- 3. HH:MM (or HH:MM-HH:MM) ----------
    time_matches = re.findall(r'(\d{1,2}):(\d{2})', text_clean)
    if len(time_matches) == 1:
        h, m = time_matches[0]
        h, m = int(h), int(m)
        if 0 <= h <= 23 and 0 <= m <= 59:
            start = now.replace(hour=h, minute=m, second=0, microsecond=0)
            return int(start.timestamp()), None
    elif len(time_matches) >= 2:
        h1, m1 = int(time_matches[0][0]), int(time_matches[0][1])
        h2, m2 = int(time_matches[1][0]), int(time_matches[1][1])
        if all(0 <= x <= 23 for x in [h1,h2]) and 0 <= m1 <= 59 and 0 <= m2 <= 59:
            start = now.replace(hour=h1, minute=m1, second=0, microsecond=0)
            end = now.replace(hour=h2, minute=m2, second=0, microsecond=0)
            if end <= start:
                end += timedelta(days=1)
            duration = int((end - start).total_seconds() / 60)
            return int(start.timestamp()), duration

    # ---------- 4. Jalali date (optional time after) ----------
    jalali_date = _parse_date_jalali(text_clean)
    if jalali_date:
        # check for a time nearby
        time_after = re.search(r'(\d{1,2}):(\d{2})', text_clean)
        if time_after:
            h, m = int(time_after.group(1)), int(time_after.group(2))
            if 0 <= h <= 23 and 0 <= m <= 59:
                jalali_date = jalali_date.replace(hour=h, minute=m)
        return int(jalali_date.timestamp()), None

    # ---------- 5. Relative dates ----------
    rel_date = _parse_relative_date(text_clean, now)
    if rel_date:
        # check for time attached
        time_match = re.search(r'(\d{1,2}):(\d{2})', text_clean)
        if time_match:
            h, m = int(time_match.group(1)), int(time_match.group(2))
            if 0 <= h <= 23 and 0 <= m <= 59:
                rel_date = rel_date.replace(hour=h, minute=m)
        return int(rel_date.timestamp()), None

    # ---------- "last X mins/hours" → start = now - X, duration = X ----------
    m = re.search(r'(?:last|past)\s+(\d+)\s*(?:min(?:ute)?s?|m)\b', text_clean)
    if m:
        minutes = int(m.group(1))
        start = now - timedelta(minutes=minutes)
        return int(start.timestamp()), minutes

    m = re.search(r'(?:last|past)\s+(\d+)\s*(?:hour(?:s)?|h)\b', text_clean)
    if m:
        hours = int(m.group(1))
        start = now - timedelta(hours=hours)
        return int(start.timestamp()), hours * 60

    # ---------- 6. nothing found ----------
    return None, None
