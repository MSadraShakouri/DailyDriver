"""Unified timeline export coordinator."""

from __future__ import annotations

import time
from itertools import groupby

from dailydriver.cli.timeline import collect_timeline_items
from dailydriver.core.database import get_connection_cm
from dailydriver.core.export_utils import parse_duration_arg
from dailydriver.ui.terminal_ui import current_ui


def _parse_duration(arg: str) -> int | None:
    """Backward-compatible wrapper around the shared duration parser."""
    return parse_duration_arg(arg)


def _range_label(duration_arg: str, days: int) -> str:
    return "all time" if duration_arg.strip().lower() == "all" else f"last {days} days"


def _render_markdown(range_label: str, items: list[dict]) -> str:
    lines = [f"# Export ({range_label})", ""]
    if not items:
        lines.append("No entries in the selected range.")
        return "\n".join(lines) + "\n"

    for date, group in groupby(items, key=lambda item: item["display_date"]):
        lines.append(f"### {date}")
        lines.append("")
        for item in group:
            lines.append(f"- **{item['text']}** – *{item['display_time']}*  ")
            details = item.get("details", "").strip()
            if details:
                for detail_line in details.splitlines():
                    lines.append(f"  > {detail_line}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_text(range_label: str, items: list[dict]) -> str:
    lines = [f"══════ Export ({range_label}) ══════", ""]
    if not items:
        lines.append("No entries in the selected range.")
        return "\n".join(lines) + "\n"

    for date, group in groupby(items, key=lambda item: item["display_date"]):
        lines.append(f"── {date} ──")
        for item in group:
            lines.append(f"  {item['display_time']}  {item['text']}")
            details = item.get("details", "").strip()
            if details:
                for detail_line in details.splitlines():
                    lines.append(f"    {detail_line}")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def export(cmd: str):
    """Usage: export <duration|all> [--txt|--md]   e.g. export 7d --md"""
    parts = cmd.strip().split()
    file_format = "md"
    duration_arg = None

    for arg in parts[1:]:
        lowered = arg.lower()
        if lowered in ("--txt", "--md"):
            file_format = lowered[2:]
        elif duration_arg is None:
            duration_arg = lowered
        else:
            current_ui.print_line("Unknown argument: " + arg)
            return None

    if not duration_arg:
        current_ui.print_line("Usage: export <duration|all> [--txt|--md]  (e.g., export 7d, export all --txt)")
        return None

    days = _parse_duration(duration_arg)
    if days is None:
        current_ui.print_line("Invalid duration. Use all, 7d, 2w, 3m, 1y, or a number.")
        return None

    cutoff = 0 if days == 0 else int(time.time()) - days * 86400

    with get_connection_cm(auto=False) as conn:
        all_items = collect_timeline_items(conn, cutoff)

    label = _range_label(duration_arg, days)
    content = _render_text(label, all_items) if file_format == "txt" else _render_markdown(label, all_items)
    filename = f"export_{duration_arg.strip().lower()}.{file_format}"
    with open(filename, "w", encoding="utf-8") as handle:
        handle.write(content)
    return f"Exported to {filename} (format: {file_format.upper()})"
