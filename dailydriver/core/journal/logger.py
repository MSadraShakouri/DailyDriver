"""Interactive free-text journal logging."""

from __future__ import annotations

import time
from datetime import datetime

from dailydriver.core.database import get_connection_cm
from dailydriver.core.export_utils import format_time_range
from dailydriver.core.state import get_active_injected_categories, get_last_action_time
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.time_parser import parse_time_expressions

from .keywords import DROPDOWN_RANKED, MAX_RESULTS, find_matching_categories
from .writer import inject_great_categories, save_entry


def _persist_new_paths(conn, paths: list[str]) -> None:
    """Insert missing paths without burning AUTOINCREMENT IDs on duplicates."""
    cur = conn.cursor()
    for path in paths:
        exists = cur.execute("SELECT 1 FROM categories WHERE path = ?", (path,)).fetchone()
        if not exists:
            cur.execute("INSERT INTO categories (path) VALUES (?)", (path,))
    conn.commit()


def _choose_categories(conn, cmd: str) -> list[str] | None:
    cur = conn.cursor()
    selected_paths: list[str] = []
    # Active state categories are already applied automatically to this entry.
    # Keep them visible as context, but out of both the numbered suggestions and
    # the rich dropdown so the user only chooses additional categories.
    injected_paths = get_active_injected_categories()
    injected_set = set(injected_paths)
    if injected_paths:
        current_ui.print_line("Already injected: " + ", ".join(injected_paths))

    # Ask for a few extra ranked results so filtering injected paths still
    # leaves a full numbered list and a useful rich dropdown when possible.
    ranked = find_matching_categories(cmd, limit=DROPDOWN_RANKED + len(injected_set))
    ranked = [(path, score) for path, score in ranked if path not in injected_set]
    matches = ranked[:MAX_RESULTS]
    ranked_paths = [path for path, _ in ranked]
    show_injected_only = bool(injected_paths and matches)

    # Rich backends (prompt_toolkit) provide an autocompleting, ranked picker.
    # It returns None to signal "fall back to the plain flow below".
    all_paths = [
        row["path"]
        for row in cur.execute("SELECT path FROM categories ORDER BY path")
        if row["path"] not in injected_set
    ]
    picked = current_ui.select_categories(matches, ranked_paths, all_paths, show_injected_only=show_injected_only)
    if picked is not None:
        _persist_new_paths(conn, picked)
        return picked

    if matches:
        current_ui.print_line()
        current_ui.print_line("Suggested categories:")
        if show_injected_only:
            current_ui.print_line("  [0] Already injected only")
        for index, (path, _) in enumerate(matches, 1):
            current_ui.print_line(f"  [{index}] {path}")
        prompt = "Enter=1, numbers to select, or type new paths"
        if show_injected_only:
            prompt = "Enter=1, 0=already injected only, numbers to select, or type new paths"
        current_ui.print_line(prompt)
        choice = current_ui.prompt("> ").strip().lower()
        if choice == "":
            selected_paths = [matches[0][0]]
        elif choice == "0" and show_injected_only:
            selected_paths = []
        else:
            for token in choice.split():
                if token == "0" and show_injected_only:
                    selected_paths = []
                    break
                if token.isdigit():
                    idx = int(token) - 1
                    if 0 <= idx < len(matches):
                        selected_paths.append(matches[idx][0])
                else:
                    _persist_new_paths(conn, [token])
                    selected_paths.append(token)
    else:
        cat_choice = current_ui.prompt("No suggestions. Enter category path (or Enter to skip): ").strip().lower()
        if cat_choice:
            selected_paths = cat_choice.split()
            _persist_new_paths(conn, selected_paths)

    return selected_paths


def log_free_text(cmd: str, started_at: int | None = None):
    with get_connection_cm() as conn:
        duration = None

        if started_at is not None:
            duration = int(time.time() - started_at) // 60
            if not current_ui.confirm_time(format_time_range(started_at, duration), ""):
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
