import time
from datetime import datetime, timedelta

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.core.travel_mode import is_travel_mode
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.prayer_times import get_approximate_times
from dailydriver.utils.time_parser import parse_prayer_args, parse_time_expressions
from dailydriver.utils.time_utils import today_jalali

from ._prayer_backlog import _update_complete_until
from ._prayer_core import current_slot


def _travel_mode_select_slot(conn, today, now):
    """Travel mode: smart slot selector. Returns slot string or None if cancelled."""
    today_j = jdatetime.date.today()
    approx = get_approximate_times(today_j.month, today_j.day)

    ADJUST_HOURS = 1

    fajr_h = approx["fajr"][0] - ADJUST_HOURS
    fajr_m = approx["fajr"][1]
    if fajr_h < 0:
        fajr_h += 24

    dhuhr_h = approx["dhuhr"][0] - ADJUST_HOURS
    dhuhr_m = approx["dhuhr"][1]
    if dhuhr_h < 0:
        dhuhr_h += 24

    maghrib_h = approx["maghrib"][0] - ADJUST_HOURS
    maghrib_m = approx["maghrib"][1]
    if maghrib_h < 0:
        maghrib_h += 24

    fajr_dt = now.replace(hour=fajr_h, minute=fajr_m, second=0, microsecond=0)
    dhuhr_dt = now.replace(hour=dhuhr_h, minute=dhuhr_m, second=0, microsecond=0)
    maghrib_dt = now.replace(hour=maghrib_h, minute=maghrib_m, second=0, microsecond=0)

    if now >= maghrib_dt:
        guessed_slot = "maghrib_isha"
    elif now >= dhuhr_dt:
        guessed_slot = "dhuhr_asr"
    else:
        guessed_slot = "fajr"

    cur = conn.cursor()
    cur.execute("SELECT prayer_slot FROM prayer_logs WHERE jalali_date = ?", (today,))
    logged_slots = {row["prayer_slot"] for row in cur.fetchall()}

    default_slot = guessed_slot
    if guessed_slot in logged_slots:
        if guessed_slot == "fajr" and "dhuhr_asr" not in logged_slots:
            default_slot = "dhuhr_asr"
        elif guessed_slot in ("fajr", "dhuhr_asr") and "maghrib_isha" not in logged_slots:
            default_slot = "maghrib_isha"

    slot_display = {
        "fajr": "Fajr",
        "dhuhr_asr": "Dhuhr & Asr",
        "maghrib_isha": "Maghrib & Isha",
    }

    current_ui.print_line("\nTravel mode: select prayer slot")
    for slot in ["fajr", "dhuhr_asr", "maghrib_isha"]:
        label = slot_display[slot]
        indicator = " (suggested)" if slot == default_slot else ""
        num = {"fajr": "1", "dhuhr_asr": "2", "maghrib_isha": "3"}[slot]
        current_ui.print_line(f"  [{num}] {label}{indicator}")
    current_ui.print_line("  [n] Cancel")
    current_ui.print_line(f"\nEnter = {slot_display[default_slot]} (smart guess)")

    choice = current_ui.prompt("> ").strip().lower()

    if choice == "":
        return default_slot
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
        return default_slot


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

        # ----- TRAVEL MODE: smart slot selector -----
        if is_travel_mode() and not explicit_time and not offset_min:
            slot = _travel_mode_select_slot(conn, today, now)
            if slot is None:
                return None
            prayer_dt = now
        else:
            # ----- Normal mode -----
            today_j = jdatetime.date.today()
            approx = get_approximate_times(today_j.month, today_j.day)
            dhuhr_dt = now.replace(hour=approx["dhuhr"][0], minute=approx["dhuhr"][1], second=0, microsecond=0)
            maghrib_dt = now.replace(
                hour=approx["maghrib"][0],
                minute=approx["maghrib"][1],
                second=0,
                microsecond=0,
            )

            if explicit_time:
                hour = explicit_time // 60
                minute = explicit_time % 60
                test_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
                if test_dt < dhuhr_dt:
                    slot = "fajr"
                elif test_dt < maghrib_dt:
                    slot = "dhuhr_asr"
                else:
                    slot = "maghrib_isha"
            else:
                slot = current_slot()

            if offset_min is not None:
                interpretations = parse_time_expressions(f"-{offset_min}", now, last_time=None)
                if interpretations:
                    prayer_dt = interpretations[0].start
                else:
                    prayer_dt = now - timedelta(minutes=offset_min)
            elif explicit_time:
                prayer_dt = now.replace(
                    hour=explicit_time // 60,
                    minute=explicit_time % 60,
                    second=0,
                    microsecond=0,
                )
            else:
                prayer_dt = now

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
