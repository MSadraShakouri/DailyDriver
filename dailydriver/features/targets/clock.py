"""Day-boundary-aware clock for all target operations."""

import jdatetime

from dailydriver.core.state import get_shifted_today


def today() -> jdatetime.date:
    return get_shifted_today()
