# dailydriver/domains/prayer_log.py
import time
from datetime import datetime, timedelta

import jdatetime

from dailydriver.core.database import get_connection_cm
from dailydriver.ui.terminal_ui import current_ui
from dailydriver.utils.prayer_times import get_approximate_times
from dailydriver.utils.time_parser import parse_prayer_args, parse_time_expressions
from dailydriver.utils.time_utils import today_jalali

from ._prayer_backlog import _update_complete_until
from ._prayer_core import current_slot


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
            time_min = parsed["explicit_time"]  # None if no time
            offset_min = parsed["offset_min"]  # None if no offset
            from ._prayer_backlog import log_qada

            log_qada(time_min, offset_min)
            return

        parsed = parse_prayer_args(args)
        offset_min = parsed["offset_min"]
        explicit_time = parsed["explicit_time"]
        jamaat_location = parsed["jamaat_location"]
        shak_count = parsed["shak_count"]

        # Get today's prayer times (interpolated)
        today_j = jdatetime.date.today()
        approx = get_approximate_times(today_j.month, today_j.day)
        now = datetime.now()
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
                # Fallback to original behaviour
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
        _update_complete_until(conn)  # update meta in same transaction
        conn.commit()

    result = f"Logged: {slot_display}\nTime:   {time_str}"
    if jamaat_location is not None:
        result += f"\nJamaat: {jamaat_location if jamaat_location else 'yes'}"
    if shak_count:
        result += f"\nShak:   {shak_count}"
    return result
