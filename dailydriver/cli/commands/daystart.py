"""Day start command – view and set day_start_hour."""

from dailydriver.core.state import get_day_start_hour, set_day_start_hour


def daystart_command(cmd: str) -> str:
    """Handle daystart command: daystart | daystart <0-23>."""
    parts = cmd.strip().split()

    if len(parts) == 1:
        hour = get_day_start_hour()
        return f"Day start: {hour:02d}:00"

    if len(parts) == 2:
        try:
            hour = int(parts[1])
        except ValueError:
            return f"Invalid hour: {parts[1]}. Must be 0-23."

        try:
            set_day_start_hour(hour)
        except ValueError:
            return f"Invalid hour: {parts[1]}. Must be 0-23."

        return f"Day start set to {hour:02d}:00"

    return "Usage: daystart          → show current\n       daystart <0-23>   → set hour"


__all__ = ["daystart_command"]
