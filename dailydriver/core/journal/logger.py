"""Interactive free-text journal logging."""

from __future__ import annotations

import time
from datetime import datetime

from dailydriver.core.database import get_connection_cm
from dailydriver.core.state import get_active_great_event, get_last_action_time
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.time_parser import parse_time_expressions

from .keywords import DROPDOWN_RANKED, MAX_RESULTS, find_matching_categories
from .writer import inject_great_categories, save_entry


def _persist_new_paths(conn, paths: list[str]) -> None:
    """Insert any category paths that do not yet exist."""
    cur = conn.cursor()
    for path in paths:
        cur.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (path,))
    conn.commit()


def _choose_categories(conn, cmd: str) -> list[str] | None:
    cur = conn.cursor()
    selected_paths: list[str] = []
    # A longer ranked list orders the rich dropdown; the short numbered list is
    # the head of it.
    ranked = find_matching_categories(cmd, limit=DROPDOWN_RANKED)
    matches = ranked[:MAX_RESULTS]
    ranked_paths = [path for path, _ in ranked]
    active_great_event = get_active_great_event()
    show_great_only = active_great_event is not None and bool(matches)

    # Rich backends (prompt_toolkit) provide an autocompleting, ranked picker.
    # It returns None to signal "fall back to the plain flow below".
    all_paths = [row["path"] for row in cur.execute("SELECT path FROM categories ORDER BY path")]
    picked = current_ui.select_categories(matches, ranked_paths, all_paths, show_great_only=show_great_only)
    if picked is not None:
        _persist_new_paths(conn, picked)
        return picked

    if matches:
        current_ui.print_line()
        current_ui.print_line("Suggested categories:")
        if show_great_only:
            current_ui.print_line("  [0] Great Event only")
        for index, (path, _) in enumerate(matches, 1):
            current_ui.print_line(f"  [{index}] {path}")
        prompt = "Enter=1, numbers to select, or type new paths"
        if show_great_only:
            prompt = "Enter=1, 0=Great Event only, numbers to select, or type new paths"
        current_ui.print_line(prompt)
        choice = current_ui.prompt("> ").strip().lower()
        if choice == "":
            selected_paths = [matches[0][0]]
        elif choice == "0" and show_great_only:
            selected_paths = []
        else:
            for token in choice.split():
                if token == "0" and show_great_only:
                    selected_paths = []
                    break
                if token.isdigit():
                    idx = int(token) - 1
                    if 0 <= idx < len(matches):
                        selected_paths.append(matches[idx][0])
                else:
                    cur.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (token,))
                    conn.commit()
                    selected_paths.append(token)
    else:
        cat_choice = current_ui.prompt("No suggestions. Enter category path (or Enter to skip): ").strip().lower()
        if cat_choice:
            for token in cat_choice.split():
                cur.execute("INSERT OR IGNORE INTO categories (path) VALUES (?)", (token,))
                conn.commit()
                selected_paths.append(token)

    return selected_paths


def log_free_text(cmd: str, started_at: int | None = None):
    with get_connection_cm() as conn:
        duration = None

        if started_at is not None:
            duration = int(time.time() - started_at) // 60
            start_str = datetime.fromtimestamp(started_at).strftime("%H:%M")
            dur_str = f"{duration // 60}h {duration % 60}m" if duration // 60 else f"{duration}m"
            if not current_ui.confirm_time(start_str, dur_str):
                return None
        else:
            now = datetime.now()
            last_ts = get_last_action_time()
            last_time = datetime.fromtimestamp(last_ts) if last_ts else None

            while True:
                interpretations = parse_time_expressions(cmd, now, last_time)
                if not interpretations:
                    current_ui.print_line("No time detected.")
                    choice = current_ui.prompt("(Enter=now, type a time expression, n=cancel) ").strip().lower()
                    if choice == "":
                        started_at = int(now.timestamp())
                        duration = None
                        break
                    if choice == "n":
                        return None
                    cmd = choice
                    continue

                if len(interpretations) == 1:
                    selected = interpretations[0]
                else:
                    current_ui.print_line("Time suggestions:")
                    for index, interpretation in enumerate(interpretations, 1):
                        current_ui.print_line(f"  [{index}] {interpretation.label}")
                    choice = (
                        current_ui.prompt("Enter=1, numbers to select, or type a new time expression (n=cancel) ")
                        .strip()
                        .lower()
                    )
                    if choice == "":
                        selected = interpretations[0]
                        started_at = int(selected.start.timestamp())
                        duration = selected.duration_minutes
                        break
                    if choice == "n":
                        return None
                    if choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(interpretations):
                            selected = interpretations[idx]
                            started_at = int(selected.start.timestamp())
                            duration = selected.duration_minutes
                            break
                        current_ui.print_line("Invalid number.")
                        continue
                    cmd = choice
                    continue

                started_at = int(selected.start.timestamp())
                duration = selected.duration_minutes
                if not current_ui.confirm_time(selected.label, ""):
                    return None
                break

        selected_paths = _choose_categories(conn, cmd) or []
        inject_great_categories(selected_paths)
        result = save_entry(conn, cmd, started_at, duration, selected_paths)
        conn.commit()
        return result
