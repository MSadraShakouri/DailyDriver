# dailydriver/features/weather/__init__.py
"""Weather feature – fetch and display Tehran weather."""
from . import _header
from . import _migrations

NAME = "weather"
VERSION = "1.0.0"

def migrations():
    return _migrations.migrations()

def header_sections(conn, today, target_date, is_today):
    """Return weather line if available."""
    line = _header.get_weather_str(conn, today, is_today)
    if line:
        return [(20, line)]   # priority 20 – after sleep/nap
    return []
