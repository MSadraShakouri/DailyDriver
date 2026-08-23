"""Markdown export for void entries."""

import time
from itertools import groupby

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.ui.terminal_ui import current_ui


def _parse_duration(arg: str) -> int | None:
    """Parse a duration string like '7d', '2w', '3m', '1y', or a bare number."""
    arg = arg.strip().lower()
    if arg.endswith("d"):
        try:
            return int(arg[:-1])
        except ValueError:
            return None
    elif arg.endswith("w"):
        try:
            return int(arg[:-1]) * 7
        except ValueError:
            return None
    elif arg.endswith("m"):
        try:
            return int(arg[:-1]) * 30
        except ValueError:
            return None
    elif arg.endswith("y"):
        try:
            return int(arg[:-1]) * 365
        except ValueError:
            return None
    elif arg.isdigit():
        return int(arg)
    return None


def export_void(cmd: str) -> str | None:
    """Export void entries to a Markdown file."""
    parts = cmd.strip().split()
    if len(parts) != 2:
        current_ui.print_line("Usage: vexport <duration>  (e.g., vexport 7d)")
        return None

    duration_arg = parts[1]
    days = _parse_duration(duration_arg)
    if days is None:
        current_ui.print_line("Invalid duration. Use 7d, 2w, 3m, 1y, or a number.")
        return None

    cutoff = int(time.time()) - days * 86400

    with get_connection_cm(auto=False) as conn:
        cur = conn.cursor()
        rows = cur.execute(
            "SELECT created_at, description FROM void_entries WHERE created_at >= ? ORDER BY created_at",
            (cutoff,),
        ).fetchall()

    if not rows:
        return "No void entries in the selected range."

    # Group by Jalali date
    grouped = []
    for row in rows:
        jd = jdatetime.datetime.fromtimestamp(row["created_at"])
        date_str = jd.strftime("%d %B %Y")  # e.g., "18 Tir 1405"
        time_str = jd.strftime("%H:%M")
        grouped.append(
            {
                "date": date_str,
                "time": time_str,
                "text": row["description"],
            }
        )

    # Build Markdown content
    lines = []
    lines.append(f"# Void Export (last {days} days)\n")
    lines.append("## Void Entries\n")

    for date, group in groupby(grouped, key=lambda r: r["date"]):
        lines.append(f"### {date}\n")
        for entry in group:
            lines.append(f"- **{entry['time']}**  ")
            lines.append(f"  > {entry['text']}")
        lines.append("")  # blank line between days

    content = "\n".join(lines)

    filename = f"export_void_{duration_arg.strip().lower()}.md"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)

    return f"Exported void entries to {filename} (Markdown)"
