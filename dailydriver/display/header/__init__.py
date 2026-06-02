# dailydriver/display/header/__init__.py
"""Daily header data builder – delegated to sub‑modules."""

from datetime import timedelta

import jdatetime
from hijridate import Gregorian as HijriGregorian

import dailydriver.features as features_pkg
from dailydriver.core.database import get_connection_cm
from dailydriver.display.display_utils import get_width, spread_line
from dailydriver.features.calendar._logic import get_hijri_offset
from dailydriver.features.events._header import get_last_entry_time
from dailydriver.utils.time_utils import format_jalali, today_jalali

from .prayer import get_prayer_nudges, get_prayer_parts


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
        corrected_greg = gdate - timedelta(days=offset)
        hijri_obj = HijriGregorian.fromdate(corrected_greg).to_hijri()
        hijri_str = f"{hijri_obj.day} {hijri_obj.month_name()} {hijri_obj.year}"
        greg_hijri_line = spread_line([greg_str, hijri_str], margins=1 / 8)

        if not is_today:
            jalali_line = f"\033[2m\033[1m{formatted}\033[0m"
            separator = f"\033[2m{separator}\033[0m"
            greg_hijri_line = f"\033[2m{greg_hijri_line}\033[0m"

        prayer_parts = get_prayer_parts(conn, today)

        prayer_nudges = get_prayer_nudges(conn, target_date, today, is_today)

        # Collect header lines from enabled feature packages
        feature_lines = []
        for feature in features_pkg.ENABLED:
            if hasattr(feature, "header_sections"):
                lines = feature.header_sections(conn, today, target_date, is_today)
                if isinstance(lines, list):
                    feature_lines.extend(lines)

        # Sort: tuples by priority, plain strings stay on top
        tupled = [item for item in feature_lines if isinstance(item, tuple)]
        plain = [item for item in feature_lines if not isinstance(item, tuple)]
        tupled.sort(key=lambda x: x[0])
        feature_lines = plain + [text for _, text in tupled]

        last_entry_time = get_last_entry_time(is_today)

        return {
            "jalali_line": jalali_line,
            "separator": separator,
            "greg_hijri_line": greg_hijri_line,
            "prayer_parts": prayer_parts,
            "feature_lines": feature_lines,
            "prayer_nudges": prayer_nudges,
            "is_today": is_today,
            "last_entry_time": last_entry_time,
        }
