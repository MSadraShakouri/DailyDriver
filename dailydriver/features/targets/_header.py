"""Header integration for targets feature."""

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.core.day_start import get_shifted_today

from . import _logic
from ._utils import get_daily_total


def get_targets_header_lines(conn):
    """Return header lines for targets that are due today.
    Shows interval goal progress only, not total progress.
    Format: 🎯 Salavat: 0/100 for today
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT id, kind, name, target_total, logged_total, interval_type, interval_value, target_per_interval, paused_until
        FROM target_entries
        ORDER BY kind, name
    """)
    entries = [dict(row) for row in cur.fetchall()]

    today = get_shifted_today()
    lines = []

    for entry in entries:
        # Skip entries without an interval
        if not entry.get("interval_type"):
            continue

        # Skip complete entries (if target is finite and reached)
        target = entry["target_total"]
        logged = entry["logged_total"]
        if target is not None and logged >= target:
            continue

        # Skip paused entries
        paused_until = entry.get("paused_until")
        if paused_until:
            try:
                y, m, d = map(int, paused_until.split("-"))
                pause_date = jdatetime.date(y, m, d)
                if pause_date >= today:
                    continue
            except (ValueError, TypeError):
                pass

        # Check if today is the due date
        next_due = _logic.compute_next_due(entry, today)
        if next_due != today:
            continue

        # Calculate today's progress
        daily_total = get_daily_total(entry["id"], today, conn=conn)
        goal = entry.get("target_per_interval")

        # Determine if already fulfilled today
        if goal is None:
            if daily_total > 0:
                continue  # Already logged today, no need to nudge
            display_goal = "any"
            progress_display = f"{daily_total}"
        else:
            if daily_total >= goal:
                continue  # Already met the goal today
            display_goal = str(goal)
            progress_display = f"{daily_total}/{goal}"

        # Build the line with emoji based on kind
        emoji = "🎯" if entry["kind"] == "nazr" else "📊"
        line = f"{emoji} {entry['name']}: {progress_display} for today"
        lines.append(line)

    return lines


def header_sections(conn, today, target_date, is_today):
    """Hook for header integration. Only shows for today."""
    if not is_today:
        return []
    lines = get_targets_header_lines(conn)
    # Priority 40 — after hygiene (30), before calendar events (45)
    return [(31, line) for line in lines]
