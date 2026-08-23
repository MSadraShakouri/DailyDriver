"""Markdown export for void entries."""

from __future__ import annotations

import time
from itertools import groupby

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.core.export_utils import parse_duration_arg
from dailydriver.ui.terminal_ui import current_ui


def _parse_duration(arg: str) -> int | None:
    """Parse a duration string like '7d', '2w', '3m', '1y', a bare number, or 'all'."""
    return parse_duration_arg(arg)



def export_void(cmd: str) -> str | None:
    """Export void entries to a Markdown file."""
    parts = cmd.strip().split()
    if len(parts) != 2:
        current_ui.print_line("Usage: vexport <duration|all>  (e.g., vexport 7d, vexport all)")
        return None

    duration_arg = parts[1]
    days = _parse_duration(duration_arg)
    if days is None:
        current_ui.print_line("Invalid duration. Use all, 7d, 2w, 3m, 1y, or a number.")
        return None

    cutoff = 0 if days == 0 else int(time.time()) - days * 86400

    with get_connection_cm(auto=False) as conn:
        rows = conn.execute(
            "SELECT created_at, description FROM void_entries WHERE created_at >= ? ORDER BY created_at",
            (cutoff,),
        ).fetchall()

    if not rows:
        return "No void entries in the selected range."

    grouped = []
    for row in rows:
        jd = jdatetime.datetime.fromtimestamp(row["created_at"])
        grouped.append(
            {
                "date": jd.strftime("%d %B %Y"),
                "time": jd.strftime("%H:%M"),
                "text": row["description"],
            }
        )

    range_label = "all time" if duration_arg.strip().lower() == "all" else f"last {days} days"
    lines = [f"# Void Export ({range_label})", ""]
    for date, group in groupby(grouped, key=lambda row: row["date"]):
        lines.append(f"### {date}")
        lines.append("")
        for entry in group:
            lines.append(f"- **Void** – *{entry['time']}*  ")
            for detail_line in entry["text"].splitlines():
                lines.append(f"  > {detail_line}")
            lines.append("")

    filename = f"export_void_{duration_arg.strip().lower()}.md"
    with open(filename, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).rstrip() + "\n")

    return f"Exported void entries to {filename} (Markdown)"
