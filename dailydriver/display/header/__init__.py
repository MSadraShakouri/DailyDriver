# dailydriver/display/header/__init__.py
"""Daily header data builder – delegated to sub‑modules."""

from datetime import timedelta

import jdatetime
from hijridate import Gregorian as HijriGregorian

import dailydriver.features as features_pkg
from dailydriver.core.database import get_connection_cm
from dailydriver.display.display_utils import get_width, spread_line
from dailydriver.display.header.events import (
    get_great_event_str,
    get_last_entry_time,
    get_running_event_str,
)
from dailydriver.features.calendar.hijri import get_hijri_offset
from dailydriver.features.registry import header_hook, validate_header_sections
from dailydriver.utils.time_utils import format_jalali, today_jalali


def build_header_data(day=None, is_today=True):
    """Collect all data needed for the daily header and return a dict."""
    with get_connection_cm() as conn:
        if day is None:
            today = today_jalali()
            target_date = jdatetime.date.today()
        else:
            today = day
            y, m, d = map(int, day.split("-"))
            target_date = jdatetime.date(y, m, d)

        formatted = format_jalali(today)
        # Prepend weekday abbreviation (e.g., "Sun, ")
        gdate = target_date.togregorian()
        weekday_abbr = gdate.strftime("%a")
        formatted = f"{weekday_abbr}, {formatted}"

        # --- new date block ---
        jalali_line = f"\033[1m{formatted}\033[0m"
        separator = "─" * (get_width() // 4)

        # Gregorian and Hijri with margins
        greg_str = gdate.strftime("%d %B %Y")
        offset = get_hijri_offset()
        corrected_greg = gdate + timedelta(days=offset)
        hijri_obj = HijriGregorian.fromdate(corrected_greg).to_hijri()
        hijri_str = f"{hijri_obj.day} {hijri_obj.month_name()} {hijri_obj.year}"
        greg_hijri_line = spread_line([greg_str, hijri_str], margins=1 / 8)

        if not is_today:
            jalali_line = f"\033[2m\033[1m{formatted}\033[0m"
            separator = f"\033[2m{separator}\033[0m"
            greg_hijri_line = f"\033[2m{greg_hijri_line}\033[0m"

        # Collect the single, explicit (priority, text) header representation.
        sections = []
        for feature in features_pkg.ENABLED:
            build_sections = header_hook(feature)
            if build_sections is not None:
                returned = build_sections(conn, today, target_date, is_today)
                sections.extend(validate_header_sections(feature, returned))

        # Great/running event status are core (not a feature package), but they
        # join the same priority-ordered stream so they render in their historic
        # slot: just under prayer (0) and above sleep (10). Priorities 5 and 6
        # match the pre-refactor events feature.
        if great_event := get_great_event_str(is_today):
            sections.append((5, great_event))
        if running_event := get_running_event_str(is_today):
            sections.append((6, running_event))

        sections.sort(key=lambda item: item[0])
        feature_lines = [text for _, text in sections]

        last_entry_time = get_last_entry_time(is_today)

        return {
            "jalali_line": jalali_line,
            "separator": separator,
            "greg_hijri_line": greg_hijri_line,
            "feature_lines": feature_lines,
            "is_today": is_today,
            "last_entry_time": last_entry_time,
        }
