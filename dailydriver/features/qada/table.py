"""Qada manager table rendering."""

import jdatetime

from dailydriver.display.display_utils import display_width, get_width, spread_line
from dailydriver.features.presentation import format_due_date, format_percentage
from dailydriver.ui.terminal_ui import current_ui


def render_entries(entries):
    """Render the qada entries table using spread_line."""
    tw = get_width()
    today_j = jdatetime.date.today()

    # Prepare all row data and track max widths
    rows = []
    max_name = display_width("Name")
    max_prog = display_width("Progress")
    max_pct = display_width("%")
    max_next = display_width("Next")

    for entry in entries:
        idx = str(entry["index"])
        name = entry["name"]
        prog = entry["progress_display"]

        pct_display = ""
        target = entry["target_total"]
        if target != -1 and entry["percentage"] is not None:
            pct_display = format_percentage(entry["percentage"])

        next_display = format_due_date(entry["next_instance"], today_j)

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
                "is_complete": entry["is_complete"],
                "is_paused": entry["is_paused"],
            }
        )

    # Build header with padded columns
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

    # Render rows
    for row in rows:
        parts = [
            " " + row["idx"].ljust(1),
            row["name"].ljust(max_name),
            row["prog"].ljust(max_prog),
            row["pct"].ljust(max_pct),
            row["next"].ljust(max_next) + " ",
        ]
        line = spread_line(parts, width=tw, margins=0)

        # Apply colors
        target = row["target"]
        if target == -1:
            line = f"\033[33m{line}\033[0m"
        elif row["is_complete"]:
            line = f"\033[32m{line}\033[0m"
        elif row["is_paused"]:
            line = f"\033[2m{line}\033[0m"

        current_ui.print_line(line)
