# dailydriver/core/logger.py
import time
from datetime import datetime

from dailydriver.core.database import get_connection_cm
from dailydriver.core.entry_writer import _save_entry, inject_great_categories
from dailydriver.core.keyword_learner import find_matching_categories
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.time_parser import parse_time_expressions

# ----------------------------------------------------------------------
#  Core free‑text logging
# ----------------------------------------------------------------------


def log_free_text(cmd, started_at=None):
    with get_connection_cm() as conn:
        cur = conn.cursor()
        selected_paths = []
        duration = None

        # ---------- step 0 – time handling ----------
        if started_at is not None:
            # chaining / great‑event end: keep existing behaviour
            duration = int(time.time() - started_at) // 60
            start_dt = datetime.fromtimestamp(started_at)
            start_str = start_dt.strftime("%H:%M")
            dur_str = f"{duration // 60}h {duration % 60}m" if duration // 60 else f"{duration}m"
            if not current_ui.confirm_time(start_str, dur_str):
                return None
        else:
            now = datetime.now()

            from dailydriver.features.events.state import get_last_action_time

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
                    elif choice == "n":
                        return None
                    else:
                        cmd = choice  # re‑parse the user's new expression
                        continue

                if len(interpretations) == 1:
                    selected = interpretations[0]
                else:
                    current_ui.print_line("Time suggestions:")
                    for i, interp in enumerate(interpretations, 1):
                        current_ui.print_line(f"  [{i}] {interp.label}")
                    choice = (
                        current_ui.prompt("Enter=1, numbers to select, or type a new time expression (n=cancel) ")
                        .strip()
                        .lower()
                    )
                    if choice == "":
                        selected = interpretations[0]
                        # User explicitly chose → skip final confirmation
                        started_at = int(selected.start.timestamp())
                        duration = selected.duration_minutes
                        break
                    elif choice == "n":
                        return None
                    elif choice.isdigit():
                        idx = int(choice) - 1
                        if 0 <= idx < len(interpretations):
                            selected = interpretations[idx]
                            # User explicitly chose → skip final confirmation
                            started_at = int(selected.start.timestamp())
                            duration = selected.duration_minutes
                            break
                        else:
                            current_ui.print_line("Invalid number.")
                            continue
                    else:
                        cmd = choice  # re‑parse the user's new expression
                        continue

                started_at = int(selected.start.timestamp())
                duration = selected.duration_minutes

                # Final confirmation (only when auto‑selected or after re‑entry)
                if not current_ui.confirm_time(selected.label, ""):
                    return None
                break

        # ---------- category suggestion ----------
        matches = find_matching_categories(cmd)
        if matches:
            current_ui.print_line()
            current_ui.print_line("Suggested categories:")
            for i, (path, _) in enumerate(matches, 1):
                current_ui.print_line(f"  [{i}] {path}")
            current_ui.print_line("Enter=1, numbers to select, or type new paths (space‑separated)")
            choice = current_ui.prompt("> ").strip().lower()
            if choice == "":
                selected_paths = [matches[0][0]]
            else:
                for token in choice.split():
                    if token.isdigit():
                        try:
                            idx = int(token) - 1
                            if 0 <= idx < len(matches):
                                selected_paths.append(matches[idx][0])
                        except ValueError:
                            pass
                    else:
                        cur.execute(
                            "INSERT OR IGNORE INTO categories (path) VALUES (?)",
                            (token,),
                        )
                        conn.commit()
                        selected_paths.append(token)
        else:
            cat_choice = current_ui.prompt("No suggestions. Enter category path (or Enter to skip): ").strip().lower()
            if cat_choice:
                for token in cat_choice.split():
                    if token:
                        cur.execute(
                            "INSERT OR IGNORE INTO categories (path) VALUES (?)",
                            (token,),
                        )
                        conn.commit()
                        selected_paths.append(token)

        # ---------- inject great‑event categories ----------
        inject_great_categories(selected_paths)

        # ---------- save entry ----------
        result = _save_entry(conn, cmd, started_at, duration, selected_paths)
        conn.commit()
        return result
