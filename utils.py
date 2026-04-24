import jdatetime

def today_jalali() -> str:
    """Return today's Jalali date as 'YYYY-MM-DD'."""
    return jdatetime.date.today().strftime('%Y-%m-%d')

def format_jalali(date_str: str) -> str:
    """Convert 'YYYY-MM-DD' to 'D Month Year'."""
    y, m, d = map(int, date_str.split('-'))
    return jdatetime.date(y, m, d).strftime('%d %B %Y')
