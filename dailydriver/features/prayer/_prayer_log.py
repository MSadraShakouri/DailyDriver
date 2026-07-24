import time
import jdatetime
from datetime import datetime, timedelta

from dailydriver.core.database import get_connection_cm
from dailydriver.core.travel_mode import is_travel_mode
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.prayer_times import get_approximate_times
from dailydriver.utils.time_parser import parse_prayer_args, parse_time_expressions
from dailydriver.utils.time_utils import today_jalali

from ._prayer_backlog import _update_complete_until
from ._prayer_core import current_slot


def _travel_mode_select_slot(conn, today):
    """
    Travel mode: suggest the next unlogged prayer slot in chronological order.
    Returns slot string or None if cancelled.
    """
    order = ["fajr", "dhuhr_asr", "maghrib_isha"]
    slot_display = {
        "fajr": "Fajr",
        "dhuhr_asr": "Dhuhr & Asr",
        "maghrib_isha": "Maghrib & Isha",
    }

    # Check what's already logged today
    cur = conn.cursor()
    cur.execute("SELECT prayer_slot FROM prayer_logs WHERE jalali_date = ?", (today,))
    logged_slots = {row["prayer_slot"] for row in cur.fetchall()}

    # Suggest the first unlogged slot (or Fajr if all are logged)
    suggested = "fajr"
    for slot in order:
        if slot not in logged_slots:
            suggested = slot
            break

    # Show menu
    current_ui.print_line("\nTravel mode: select prayer slot")
    for i, slot in enumerate(order, 1):
        label = slot_display[slot]
        indicator = " (suggested)" if slot == suggested else ""
        current_ui.print_line(f"  [{i}] {label}{indicator}")
    current_ui.print_line("  [n] Cancel")
    current_ui.print_line(f"\nEnter = {slot_display[suggested]} (smart guess)")

    choice = current_ui.prompt("> ").strip().lower()

    if choice == "":
        return suggested
    elif choice == "n":
        return None
    elif choice in ("1", "f", "fajr"):
        return "fajr"
    elif choice in ("2", "d", "dhuhr"):
        return "dhuhr_asr"
    elif choice in ("3", "m", "maghrib"):
        return "maghrib_isha"
    else:
        current_ui.print_line("Invalid choice. Using default.")
        return suggested


def log_prayer(cmd: str):
    with get_connection_cm() as conn:
        cur = conn.cursor()
        today = today_jalali()

        parts = cmd.strip().split()
        args = parts[1:] if len(parts) > 1 else []

        # Handle qada logging: p q [time]
        if "q" in args:
            args.remove("q")
            parsed = parse_prayer_args(args)
            time_min = parsed["explicit_time"]
            offset_min = parsed["offset_min"]
            from ._prayer_backlog import log_qada
            log_qada(time_min, offset_min)
            return

        parsed = parse_prayer_args(args)
        offset_min = parsed["offset_min"]
        explicit_time = parsed["explicit_time"]
        jamaat_location = parsed["jamaat_location"]
        shak_count = parsed["shak_count"]
        now = datetime.now()

        # ----- Step 1: Calculate prayer time (common to both modes) -----
        if offset_min is not None:
            interpretations = parse_time_expressions(f"-{offset_min}", now, last_time=None)
            if interpretations:
                prayer_dt = interpretations[0].start
            else:
                prayer_dt = now - timedelta(minutes=offset_min)
        elif explicit_time is not None:
            prayer_dt = now.replace(
                hour=explicit_time // 60,
                minute=explicit_time % 60,
                second=0,
                microsecond=0,
            )
        else:
            prayer_dt = now

        # ----- Step 2: Determine slot -----
        if is_travel_mode():
            # Travel mode: order-based selector (always shows menu)
            slot = _travel_mode_select_slot(conn, today)
            if slot is None:
                return None
        else:
            # Normal mode: guess slot from prayer time using Tehran interpolation
            today_j = jdatetime.date.today()
            approx = get_approximate_times(today_j.month, today_j.day)
            dhuhr_dt = now.replace(hour=approx["dhuhr"][0], minute=approx["dhuhr"][1], second=0, microsecond=0)
            maghrib_dt = now.replace(
                hour=approx["maghrib"][0],
                minute=approx["maghrib"][1],
                second=0,
                microsecond=0,
            )

            # Use prayer_dt for slot guessing (not now)
            if prayer_dt < dhuhr_dt:
                slot = "fajr"
            elif prayer_dt < maghrib_dt:
                slot = "dhuhr_asr"
            else:
                slot = "maghrib_isha"

        time_str = prayer_dt.strftime("%H:%M")
        slot_display = slot.replace("_", " & ").title()

        flag_parts = []
        if jamaat_location is not None:
            loc_display = jamaat_location if jamaat_location else "yes"
            flag_parts.append(f"Jamaat ({loc_display})")
        if shak_count > 0:
            flag_parts.append(f"Shak ({shak_count})")
        extra = ", ".join(flag_parts)

        message = f"{slot_display} at {time_str}"
        if extra:
            message += f" [{extra}]"
        message += "?"

        if not current_ui.confirm(message):
            return None

        cur.execute(
            "SELECT id, prayer_time FROM prayer_logs WHERE prayer_slot=? AND jalali_date=?",
            (slot, today),
        )
        existing = cur.fetchone()
        if existing:
            old_time = datetime.fromtimestamp(existing["prayer_time"]).strftime("%H:%M")
            confirm_replace = current_ui.confirm(
                f"⚠️  Already logged at {old_time}. Overwrite? (Enter=yes, n=cancel): ",
                default_yes=True,
            )
            if not confirm_replace:
                return None
            cur.execute("DELETE FROM prayer_logs WHERE id=?", (existing["id"],))

        cur.execute(
            """INSERT INTO prayer_logs
               (prayer_slot, jalali_date, status, logged_at, prayer_time,
                jamaat_location, shak_count)
               VALUES (?,?,?,?,?,?,?)""",
            (
                slot,
                today,
                "on_time",
                int(time.time()),
                int(prayer_dt.timestamp()),
                jamaat_location,
                shak_count,
            ),
        )
        _update_complete_until(conn)
        conn.commit()

    result = f"Logged: {slot_display}\nTime:   {time_str}"
    if jamaat_location is not None:
        result += f"\nJamaat: {jamaat_location if jamaat_location else 'yes'}"
    if shak_count:
        result += f"\nShak:   {shak_count}"
    return result
