"""Prayer window nudges: pre-alert, green/yellow/red progress, and overdue."""

from __future__ import annotations

import math
from datetime import datetime

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


def get_prayer_nudges(conn, target_date, today_str, is_today, now=None):
    """Return colored nudge lines for today's prayer windows (plus past overdue).

    Per slot, in order: yellow pre-alert shortly before the window opens, a
    single-colored countdown line while the window is open (green inside the
    fadilat window, yellow for the gap, red for the final stretch), a red
    overdue line after the deadline, and nothing once logged.
    """
    if not is_today:
        return []

    if is_travel_mode():
        return _get_travel_next_nudge(conn, today_str)

    if now is None:
        now = datetime.now()

    nudges = []
    info = resolve_city(conn, now)
    windows = get_slot_windows(now.date(), info.lat, info.lon, info.tz)

    for slot in PRAYER_SLOTS:
        if has_prayer_log(conn, slot, today_str):
            continue
        label = SLOT_LABELS[slot]
        window = windows[slot]

        if now < window.opens:
            seconds_until = (window.opens - now).total_seconds()
            if 0 <= seconds_until <= 60 * 60:
                if seconds_until < 60:
                    timing = "due now"
                else:
                    # Round upward so the nudge never claims the prayer is
                    # sooner than the minute-level schedule says it is.
                    minutes_until = math.ceil(seconds_until / 60)
                    timing = f"in ~{minutes_until} min"
                nudges.append(f"{YELLOW}🕌 {label} — {timing}{RESET}")
        elif now < window.deadline:
            # The whole line shares one color; urgency is carried by the
            # color, the shown time is always the window deadline.
            color = RED if now >= window.red_from else (YELLOW if now >= window.green_until else GREEN)
            nudges.append(f"{color}🕌 {label} — until {window.deadline.strftime('%H:%M')}{RESET}")
        else:
            nudges.append(f"{RED}⚠️ {label} not logged (today){RESET}")

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
    slots = PRAYER_SLOTS

    for slot in slots:
        if not has_prayer_log(conn, slot, today_str):
            display = SLOT_LABELS[slot]
            return [f"{RED}⚠️ {display} not logged (today){RESET}"]
    return []
