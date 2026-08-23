"""Targets manager table rendering."""

from dailydriver.display.display_utils import display_width, get_width, spread_line
from dailydriver.features.presentation import format_due_date, format_percentage, is_paused
from dailydriver.ui.terminal_ui import current_ui

from . import clock
from .schedule import compute_next_due


def render_entries(entries):
    """Render the targets entries table using spread_line."""
    tw = get_width()
    today_j = clock.today()

    rows = []
    max_name = display_width("Name")
    max_prog = display_width("Progress")
    max_pct = display_width("%")
    max_next = display_width("Next")

    for entry in entries:
        idx = str(entry["id"])
        name = entry["name"]

        target = entry["target_total"]
        logged = entry["logged_total"]

        if target is not None:
            prog = f"{logged:,}/{target:,}"
        else:
            prog = f"{logged:,}/∞"

        pct_display = ""
        if target is not None and target > 0:
            pct_display = format_percentage((logged / target) * 100)

        next_due = compute_next_due(entry, today_j)
        next_display = format_due_date(next_due, today_j)

        max_name = max(max_name, display_width(name))
        max_prog = max(max_prog, display_width(prog))
        max_pct = max(max_pct, display_width(pct_display))
        max_next = max(max_next, display_width(next_display))

        rows.append(
            {
                "idx": idx,
                "name": name,
                "prog": prog,
                "pct": pct_display,
                "next": next_display,
                "target": target,
                "logged": logged,
                "is_complete": target is not None and logged >= target,
                "is_paused": is_paused(entry, today_j),
                "has_interval": entry.get("interval_type") is not None,
            }
        )

    header_parts = [
        " " + "#".center(1),
        "Name".center(max_name),
        "Progress".center(max_prog),
        "%".center(max_pct),
        "Next".center(max_next) + " ",
    ]
    header = spread_line(header_parts, width=tw, margins=0)
    current_ui.print_line(header)
    current_ui.print_line("─" * tw)

    for row in rows:
        parts = [
            " " + row["idx"].ljust(1),
            row["name"].ljust(max_name),
            row["prog"].ljust(max_prog),
            row["pct"].ljust(max_pct),
            row["next"].ljust(max_next) + " ",
        ]
        line = spread_line(parts, width=tw, margins=0)

        if row["is_complete"]:
            line = f"\033[32m{line}\033[0m"
        elif row["is_paused"]:
            line = f"\033[2m{line}\033[0m"
        elif row["target"] is None:
            # Indefinite habit — shows as normal, no special color
            pass

        current_ui.print_line(line)
