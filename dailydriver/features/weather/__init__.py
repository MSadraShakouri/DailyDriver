"""Weather feature adapter."""

from .header import get_weather_str
from .migrations import migrations

NAME = "weather"
VERSION = "1.0.0"


def header_sections(conn, today, target_date, is_today):
    line = get_weather_str(conn, today, is_today)
    return [(20, line)] if line else []
