"""Prayer window nudges: next-prayer, pre-alert, green/yellow/red progress, overdue.

Line grammar (two rows for open windows):

* open window, green:
  ``🕌 Fajr``
  ``   fadilat till 04:48 · sunrise 05:53``
* open window, yellow:
  ``🕌 Fajr``
  ``   normal till 05:23 · sunrise 05:53``
* open window, red (late):
  ``🕌 Fajr``
  ``   late till sunrise (05:53)``  (band end == deadline)

The band name (fadilat, normal, late) is explicitly stated on the second line,
and both lines are painted in the band's color (green, yellow, red).
* nothing pending:     ``🕌 Maghrib at 18:18 (2h 30m left)``   (tomorrow's Fajr when all logged)
* pre-alert (≤60 min): ``🕌 Maghrib — in 12m (18:18)`` / ``— due now (18:18)``
* overdue:             ``⚠️ Fajr not logged (today)``

Durations are compact (``45m``, ``2h 30m``) and always rounded upward so the
line never claims the prayer is sooner than the schedule says.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import jdatetime

from dailydriver.core.location.resolver import resolve_city
from dailydriver.core.state import get_prayer_complete_until, is_travel_mode

from .schedule import PRAYER_SLOTS, SLOT_LABELS
from .store import has_prayer_log
from .windows import get_slot_windows

GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

_PRE_ALERT_MINUTES = 60
_DEADLINE_NAMES = {"fajr": "sunrise", "dhuhr_asr": "sunset", "maghrib_isha": "midnight"}


def _compact(minutes: int) -> str:
    """Compact duration: ``45m``, ``2h``, ``2h 30m``."""
    if minutes < 60:
        return f"{minutes}m"
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m" if mins else f"{hours}h"


def _band_text(slot: str, window, now: datetime) -> tuple[str, str]:
    """Return (color, band description) for an open window."""
    deadline_name = _DEADLINE_NAMES[slot]
    if now >= window.red_from:
        return RED, f"late till {deadline_name} ({window.deadline:%H:%M})"
    if now >= window.green_until:
        return YELLOW, f"normal till {window.red_from:%H:%M} · {deadline_name} {window.deadline:%H:%M}"
    return GREEN, f"fadilat till {window.green_until:%H:%M} · {deadline_name} {window.deadline:%H:%M}"


def _next_line(slot: str, window, now: datetime) -> str:
    """Next-prayer line; yellow inside the pre-alert hour.

    One grammar for both states: '🕌 Next: Maghrib 18:18 (in 2h 30m)',
    with the remaining time always in parentheses ('(due now)' under a
    minute) and the color carrying the urgency.
    """
    seconds = (window.opens - now).total_seconds()
    minutes = max(1, math.ceil(seconds / 60))
    at = window.opens.strftime("%H:%M")
    timing = "due now" if seconds < 60 else f"in {_compact(minutes)}"
    line = f"🕌 Next: {SLOT_LABELS[slot]} {at} ({timing})"
    return f"{YELLOW}{line}{RESET}" if seconds <= _PRE_ALERT_MINUTES * 60 else line


def get_prayer_nudges(conn, target_date, today_str, is_today, now=None):
    """Return today's prayer lines (plus past-day overdue), in order: the open
    window's band line or the next prayer, then today's overdue, then past."""
    if not is_today:
        return []

    if is_travel_mode():
        return _get_travel_next_nudge(conn, today_str)

    if now is None:
        now = datetime.now()

    info = resolve_city(conn, now)
    windows = get_slot_windows(now.date(), info.lat, info.lon, info.tz)

    pending = None  # (slot, window) with opens <= now < deadline, unlogged
    upcoming = None  # nearest unlogged slot opening after now
    overdue = []
    for slot in PRAYER_SLOTS:
        if has_prayer_log(conn, slot, today_str):
            continue
        window = windows[slot]
        if window.opens <= now < window.deadline:
            pending = (slot, window)
        elif window.opens > now:
            if upcoming is None or window.opens < upcoming[1].opens:
                upcoming = (slot, window)
        else:
            overdue.append(f"{RED}⚠️ {SLOT_LABELS[slot]} not logged (today){RESET}")

    nudges = []
    if pending is not None:
        slot, window = pending
        color, band = _band_text(slot, window, now)
        nudges.append(f"{color}🕌 {SLOT_LABELS[slot]}{RESET}")
        nudges.append(f"{color}   {band}{RESET}")
    elif upcoming is not None:
        nudges.append(_next_line(upcoming[0], upcoming[1], now))
    else:
        # Everything today is logged or gone: point at tomorrow's Fajr.
        tomorrow = get_slot_windows(now.date() + timedelta(days=1), info.lat, info.lon, info.tz)
        nudges.append(_next_line("fajr", tomorrow["fajr"], now))

    nudges.extend(overdue)
    nudges.extend(_get_past_overdue_nudges(conn, target_date))
    return nudges[:5]


def _get_past_overdue_nudges(conn, target_date):
    """Past-day overdue scan (up to five lines total including today's)."""
    complete_until = get_prayer_complete_until(conn=conn)
    if complete_until:
        cu_y, cu_m, cu_d = map(int, complete_until.split("-"))
        complete_j = jdatetime.date(cu_y, cu_m, cu_d)
    else:
        complete_j = target_date - jdatetime.timedelta(days=6)

    nudges = []
    count = 0
    d = target_date - jdatetime.timedelta(days=1)
    while d > complete_j and count < 5:
        date_str = d.strftime("%Y-%m-%d")
        day_label = d.strftime("%d %b")
        for slot in PRAYER_SLOTS:
            if count >= 5:
                break
            if not has_prayer_log(conn, slot, date_str):
                nudges.append(f"{RED}⚠️ {SLOT_LABELS[slot]} not logged ({day_label}){RESET}")
                count += 1
        d -= jdatetime.timedelta(days=1)
    return nudges


def _get_travel_next_nudge(conn, today_str):
    """Return a single overdue-style nudge for the first unlogged prayer slot today (travel mode only)."""
    for slot in PRAYER_SLOTS:
        if not has_prayer_log(conn, slot, today_str):
            display = SLOT_LABELS[slot]
            return [f"{RED}⚠️ {display} not logged (today){RESET}"]
    return []
