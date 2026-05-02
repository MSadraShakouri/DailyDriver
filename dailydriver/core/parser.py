# dailydriver/core/parser.py
import re
from datetime import datetime, timedelta
from dailydriver.core.date_parser import _parse_date_jalali, _parse_relative_date
from dailydriver.utils.time_parser import parse_time

def extract_time(text: str):
    """
    Scan the whole text for any time/date expressions.
    Returns (started_at_timestamp, duration_minutes) or (None, None).
    """
    now = datetime.now()
    text_clean = text.strip()

    # ---------- 0. "last X mins/hours" ----------
    m = re.search(r'(?:last|past)\s+(\d+)\s*min(?:ute)?s?', text_clean, re.IGNORECASE)
    if not m:
        m = re.search(r'(?:last|past)\s+(\d+)\s+m\b', text_clean, re.IGNORECASE)
    if m:
        minutes = int(m.group(1))
        start = now - timedelta(minutes=minutes)
        return int(start.timestamp()), minutes

    m = re.search(r'(?:last|past)\s+(\d+)\s*(?:hour(?:s)?|h)\b', text_clean, re.IGNORECASE)
    if m:
        hours = int(m.group(1))
        start = now - timedelta(hours=hours)
        return int(start.timestamp()), hours * 60

    # ---------- 1. Offsets ( -30m, -1h ) ----------
    # Try to extract a standalone offset word from the beginning/anywhere
    for word in text_clean.split():
        if word.startswith('-'):
            parsed = parse_time(word, now)
            if parsed is not None:
                return int(parsed.timestamp()), None

    # ---------- 2. Time range like 17-02 ----------
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
                start -= timedelta(days=1)
            duration = int((now - start).total_seconds() / 60)
            return int(start.timestamp()), duration

    # ---------- 3. HH:MM (single or range) ----------
    time_matches = re.findall(r'(\d{1,2}):(\d{2})', text_clean)
    if len(time_matches) == 1:
        h, m = int(time_matches[0][0]), int(time_matches[0][1])
        parsed = parse_time(f"{h:02d}:{m:02d}", now)
        if parsed is not None:
            return int(parsed.timestamp()), None
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
        time_after = re.search(r'(\d{1,2}):(\d{2})', text_clean)
        if time_after:
            h, m = int(time_after.group(1)), int(time_after.group(2))
            if 0 <= h <= 23 and 0 <= m <= 59:
                jalali_date = jalali_date.replace(hour=h, minute=m)
        return int(jalali_date.timestamp()), None

    # ---------- 5. Relative dates ----------
    rel_date = _parse_relative_date(text_clean, now)
    if rel_date:
        time_match = re.search(r'(\d{1,2}):(\d{2})', text_clean)
        if time_match:
            h, m = int(time_match.group(1)), int(time_match.group(2))
            if 0 <= h <= 23 and 0 <= m <= 59:
                rel_date = rel_date.replace(hour=h, minute=m)
        return int(rel_date.timestamp()), None

    # ---------- 6. nothing found ----------
    return None, None
