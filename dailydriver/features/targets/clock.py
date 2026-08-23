"""Day-boundary-aware clock for all target operations."""

import jdatetime

from dailydriver.core.day_start import get_shifted_today


def today() -> jdatetime.date:
    return get_shifted_today()
