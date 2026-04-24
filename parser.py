import re
from datetime import datetime, timedelta

def extract_time(text: str):
    """
    Returns (started_at_timestamp, duration_minutes) or (None, None).
    Parse patterns: HH:MM, HH:MM-HH:MM, -30m, -1h, yesterday, wed, last wed, 1404/02/03, 17-02
    """
    now = datetime.now()
    text_original = text.strip().lower()

    # Offset: -30m, -2h
    m = re.match(r'^-(\d+)\s*[mM](?:inutes?)?', text_original)
    if not m:
        m = re.match(r'^-(\d+)\s*[hH](?:ours?)?', text_original)
    if m:
        num = int(m.group(1))
        unit = 'h' if 'h' in m.group(0) else 'm'
        if unit == 'h':
            return int((now - timedelta(hours=num)).timestamp()), None
        else:
            return int((now - timedelta(minutes=num)).timestamp()), None

    # Range 17-02
    range_match = re.match(r'^(\d{1,2})-(\d{1,2})(?::(\d{2}))?', text_original)
    if range_match:
        h1, h2 = int(range_match.group(1)), int(range_match.group(2))
        m1 = m2 = 0
        if range_match.group(3):
            m2 = int(range_match.group(3))
        start = now.replace(hour=h1, minute=m1, second=0, microsecond=0)
        end = now.replace(hour=h2, minute=m2, second=0, microsecond=0)
        if end <= start:
            end += timedelta(days=1)
        duration = int((end - start).total_seconds() / 60)
        return int(start.timestamp()), duration

    # HH:MM or HH:MM-HH:MM
    time_pattern = re.findall(r'(\d{1,2}):(\d{2})', text_original)
    if len(time_pattern) == 1:
        h, m = time_pattern[0]
        start = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        return int(start.timestamp()), None
    elif len(time_pattern) == 2:
        h1, m1 = time_pattern[0]
        h2, m2 = time_pattern[1]
        start = now.replace(hour=int(h1), minute=int(m1), second=0, microsecond=0)
        end = now.replace(hour=int(h2), minute=int(m2), second=0, microsecond=0)
        if end <= start:
            end += timedelta(days=1)
        duration = int((end - start).total_seconds() / 60)
        return int(start.timestamp()), duration

    # Relative days: yesterday, wed, last wed (simple)
    if 'yesterday' in text_original:
        yesterday = now - timedelta(days=1)
        return int(yesterday.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()), None
    for day in ['sat','sun','mon','tue','wed','thu','fri']:
        if f'last {day}' in text_original:
            days_ago = (now.weekday() - ['mon','tue','wed','thu','fri','sat','sun'].index(day)) % 7 + 7
            target_date = now - timedelta(days=days_ago)
            return int(target_date.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()), None
        elif day in text_original and f'last {day}' not in text_original:
            # just the day name -> previous occurrence
            target_weekday = ['mon','tue','wed','thu','fri','sat','sun'].index(day)
            days_ago = (now.weekday() - target_weekday) % 7
            if days_ago == 0:
                days_ago = 7
            target_date = now - timedelta(days=days_ago)
            return int(target_date.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()), None

    # Jalali date: 1404/02/03 (optional time following it)
    jalali_match = re.search(r'(\d{4})/(\d{2})/(\d{2})', text_original)
    if jalali_match:
        # Convert to Gregorian using jdatetime
        import jdatetime
        y, m, d = map(int, jalali_match.groups())
        try:
            jdate = jdatetime.date(y, m, d)
            gdate = jdate.togregorian()
            start_dt = datetime(gdate.year, gdate.month, gdate.day)
            # optional time after date: look for HH:MM
            time_after = re.search(r'(\d{1,2}):(\d{2})', text_original[jalali_match.end():])
            if time_after:
                start_dt = start_dt.replace(hour=int(time_after.group(1)), minute=int(time_after.group(2)))
            return int(start_dt.timestamp()), None
        except:
            pass

    return None, None
